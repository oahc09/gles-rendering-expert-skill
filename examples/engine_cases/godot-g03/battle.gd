extends Node3D

const SEED := 1337
const BOOT_CAPACITY := 12
const STRESS_CAPACITY := 48
const SENTINEL := Vector3(0.0, 0.55, 0.0)
const PARTICLE_COUNT := 20

var unit_mesh := MultiMesh.new()
var particle_mesh := MultiMesh.new()
var camera := Camera3D.new()
var hud := Label.new()
var sentinel_body := StaticBody3D.new()
var offsets: Array[Vector3] = []
var phases: Array[float] = []
var cpu_update_usec: Array[int] = []
var stage_frames: Array[Dictionary] = []


func colored_surface(color: Color, unlit: bool) -> StandardMaterial3D:
	var surface := StandardMaterial3D.new()
	surface.albedo_color = color
	if unlit:
		surface.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return surface


func setup_scene() -> void:
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-58, -36, 0)
	light.shadow_enabled = true
	light.light_energy = 1.1
	add_child(light)

	var floor_mesh := MeshInstance3D.new()
	var ground := BoxMesh.new()
	ground.size = Vector3(26, 0.1, 24)
	ground.material = colored_surface(Color("#344968"), false)
	floor_mesh.mesh = ground
	floor_mesh.position.y = -0.05
	add_child(floor_mesh)

	var unit := BoxMesh.new()
	unit.size = Vector3(0.85, 1.1, 0.85)
	unit.material = colored_surface(Color("#ffbf33"), true)
	unit_mesh.transform_format = MultiMesh.TRANSFORM_3D
	unit_mesh.mesh = unit
	unit_mesh.instance_count = BOOT_CAPACITY
	unit_mesh.custom_aabb = AABB(Vector3(-6, 0, -6), Vector3(12, 2, 11))
	unit_mesh.visible_instance_count = 0
	var army := MultiMeshInstance3D.new()
	army.multimesh = unit_mesh
	add_child(army)

	var particle := SphereMesh.new()
	particle.radius = 0.09
	particle.height = 0.18
	particle.radial_segments = 6
	particle.rings = 3
	particle.material = colored_surface(Color("#36e7fc"), true)
	particle_mesh.transform_format = MultiMesh.TRANSFORM_3D
	particle_mesh.mesh = particle
	particle_mesh.instance_count = PARTICLE_COUNT
	var sparks := MultiMeshInstance3D.new()
	sparks.multimesh = particle_mesh
	sparks.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sparks)

	var collision := CollisionShape3D.new()
	var bounds := BoxShape3D.new()
	bounds.size = unit.size
	collision.shape = bounds
	sentinel_body.position = SENTINEL
	sentinel_body.add_child(collision)
	add_child(sentinel_body)

	var random := RandomNumberGenerator.new()
	random.seed = SEED
	for i in STRESS_CAPACITY:
		offsets.append(Vector3(float(i % 8) * 1.25 - 4.5, 0.55, float(i >> 3) * 1.4 - 5.0))
		phases.append(random.randf_range(0, TAU))
	add_child(camera)
	camera.current = true
	camera.fov = 46
	var overlay := CanvasLayer.new()
	add_child(overlay)
	overlay.add_child(hud)
	hud.position = Vector2(16, 12)
	hud.add_theme_font_size_override("font_size", 20)


func update_frame(frame: int, count: int) -> void:
	var begin := Time.get_ticks_usec()
	if count > unit_mesh.instance_count:
		unit_mesh.instance_count = count
	sentinel_body.collision_layer = 1 if count > 0 else 0
	for i in count:
		var position := SENTINEL
		if i:
			position = offsets[i] + Vector3(sin(float(frame) * 0.1 + phases[i]) * 0.2, 0, 0)
		unit_mesh.set_instance_transform(i, Transform3D(Basis.IDENTITY, position))
	unit_mesh.visible_instance_count = count
	for i in PARTICLE_COUNT:
		var phase := phases[i] + float(frame) * 0.1
		var radius := 0.7 + float(i % 4) * 0.2
		var position := Vector3(cos(phase) * radius, 1.0 + abs(sin(phase)), sin(phase) * radius)
		particle_mesh.set_instance_transform(i, Transform3D(Basis.IDENTITY, position))
	camera.position = Vector3(sin(float(frame) * 0.018) * 2.2, 5.8, 9.5)
	camera.look_at(Vector3(0, 0.5, -1))
	hud.text = "BATTLE REPLAY  |  UNITS %02d  |  SEED %d" % [count, SEED]
	cpu_update_usec.append(Time.get_ticks_usec() - begin)


func measure_stage(frame: int, count: int, output: String) -> void:
	update_frame(frame, count)
	await get_tree().physics_frame
	await RenderingServer.frame_post_draw
	var projected := camera.unproject_position(SENTINEL)
	var origin := camera.project_ray_origin(projected)
	var direction := camera.project_ray_normal(projected)
	var ray := PhysicsRayQueryParameters3D.create(origin, origin + direction * 50, 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(ray)
	var picked: bool = hit.get("collider") == sentinel_body

	var image := get_viewport().get_texture().get_image()
	var yellow_pixels := 0
	var cyan_pixels := 0
	var hud_pixels := 0
	var snapshot_written := output == ""
	if image != null and not image.is_empty():
		for y in range(image.get_height()):
			for x in range(image.get_width()):
				var color := image.get_pixel(x, y)
				if color.r > 0.8 and color.g > 0.5 and color.b < 0.35:
					yellow_pixels += 1
				if color.r < 0.45 and color.g > 0.75 and color.b > 0.8:
					cyan_pixels += 1
				if x < 430 and 8 < y and y < 44 and minf(minf(color.r, color.g), color.b) > 0.85:
					hud_pixels += 1
		if output != "":
			var saved := image.save_png(output + ".frame-%03d.png" % frame)
			snapshot_written = saved == OK
			if saved != OK:
				push_error("Could not save replay snapshot: %s" % saved)
	stage_frames.append({"frame": frame, "visible_units": unit_mesh.visible_instance_count,
		"capacity": unit_mesh.instance_count, "picked_sentinel": picked, "yellow_pixels": yellow_pixels,
		"cyan_pixels": cyan_pixels, "hud_pixels": hud_pixels, "snapshot_written": snapshot_written,
		"draw_calls_observed": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)})


func _ready() -> void:
	setup_scene()
	var output := ""
	var required_driver := ""
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--receipt="):
			output = argument.trim_prefix("--receipt=")
		elif argument.begins_with("--require-driver="):
			required_driver = argument.trim_prefix("--require-driver=")
	await measure_stage(0, 0, output)
	await measure_stage(24, BOOT_CAPACITY, output)
	await measure_stage(48, STRESS_CAPACITY, output)
	await measure_stage(72, BOOT_CAPACITY, output)
	var passed := RenderingServer.get_current_rendering_method() == "gl_compatibility"
	var driver := RenderingServer.get_current_rendering_driver_name()
	passed = passed and (required_driver == "" or required_driver == driver)
	var counts := [0, BOOT_CAPACITY, STRESS_CAPACITY, BOOT_CAPACITY]
	for index in stage_frames.size():
		var row := stage_frames[index]
		passed = passed and row["visible_units"] == counts[index] and row["picked_sentinel"] == (index != 0)
		passed = passed and row["hud_pixels"] > 40 and row["cyan_pixels"] > 10 and row["snapshot_written"]
		passed = passed and (row["yellow_pixels"] > 200 if index else row["yellow_pixels"] == 0)
	passed = passed and stage_frames[2]["capacity"] == STRESS_CAPACITY and stage_frames[3]["capacity"] == STRESS_CAPACITY
	var receipt := {"schema": "gles.g03-replay/v1", "status": "PASS" if passed else "FAIL",
		"engine": Engine.get_version_info(), "renderer": RenderingServer.get_current_rendering_method(),
		"driver": driver, "required_driver": required_driver,
		"adapter": RenderingServer.get_video_adapter_name(), "platform": OS.get_name(),
		"seed": SEED, "stages": stage_frames, "cpu_transform_update_usec": cpu_update_usec,
		"gpu_time_usec": null, "upload_time_usec": null,
		"inputs": {"project.godot": FileAccess.get_sha256("res://project.godot"),
			"battle.tscn": FileAccess.get_sha256("res://battle.tscn"),
			"battle.gd": FileAccess.get_sha256("res://battle.gd")}}
	var encoded := JSON.stringify(receipt, "  ")
	if output != "":
		var file := FileAccess.open(output, FileAccess.WRITE)
		if file == null:
			push_error("Could not write replay receipt")
			get_tree().quit(2)
			return
		file.store_string(encoded + "\n")
	print(encoded)
	if output != "":
		get_tree().quit(0 if passed else 1)
