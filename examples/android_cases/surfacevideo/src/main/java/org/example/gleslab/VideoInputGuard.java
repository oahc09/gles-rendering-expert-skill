package org.example.gleslab;

import android.graphics.SurfaceTexture;
import android.opengl.EGL14;
import android.opengl.EGLContext;
import android.opengl.EGLDisplay;
import android.opengl.EGLSurface;
import android.opengl.GLES30;
import android.opengl.Matrix;
import java.util.HashSet;
import java.util.Set;

/** Companion to ExternalSurfaceActivity; call only on its owning/current GL thread.
 * No DRM decryption, protected readback, or protected producer is implemented. */
public final class VideoInputGuard {
    private VideoInputGuard() {}
    public static Set<String> glExtensions() {
        int[] n=new int[1];GLES30.glGetIntegerv(GLES30.GL_NUM_EXTENSIONS,n,0);
        Set<String> out=new HashSet<>();
        for(int i=0;i<n[0];i++)out.add(GLES30.glGetStringi(GLES30.GL_EXTENSIONS,i));
        return out;
    }
    public static String select(boolean protectedInput, String matrix, String range, String transfer) {
        if(protectedInput)return "BLOCKED_PROTECTED_PIPELINE";
        if(matrix==null||range==null||transfer==null)return "BLOCKED_UNKNOWN_COLOR";
        if(!(matrix.equals("BT601")||matrix.equals("BT709")||matrix.equals("BT2020")||matrix.equals("RGB"))
                ||!(range.equals("limited")||range.equals("full")))return "BLOCKED_UNKNOWN_COLOR";
        if(!transfer.equals("SDR"))return "BLOCKED_HDR_TONEMAP_REQUIRED";
        Set<String> ext=glExtensions();
        return ext.contains("GL_OES_EGL_image_external")&&ext.contains("GL_OES_EGL_image_external_essl3")
                ?"EXTERNAL_ESSL3":"UNSUPPORTED_EXTERNAL";
    }
    // Diagnostic only. Extension + protected flags do not establish DRM trust,
    // protected producer/imported image validity, nor permission to read pixels.
    public static boolean protectedContextAndSurface(EGLDisplay display,EGLContext context,EGLSurface surface) {
        String text=EGL14.eglQueryString(display,EGL14.EGL_EXTENSIONS);
        if(text==null||!java.util.Arrays.asList(text.split("\\s+")).contains("EGL_EXT_protected_content"))return false;
        int[] c=new int[1],s=new int[1];
        return EGL14.eglQueryContext(display,context,0x32C0,c,0)&&EGL14.eglQuerySurface(display,surface,0x32C0,s,0)
                &&c[0]==EGL14.EGL_TRUE&&s[0]==EGL14.EGL_TRUE;
    }
    public static void acquireFrame(SurfaceTexture input,float[] output,int extraRotation,boolean rotationAlreadyBaked) {
        if(output==null||output.length!=16||(extraRotation!=0&&extraRotation!=90&&extraRotation!=180&&extraRotation!=270))throw new IllegalArgumentException("matrix/rotation");
        if(rotationAlreadyBaked&&extraRotation!=0)throw new IllegalArgumentException("Would apply rotation twice");
        input.updateTexImage(); // acquire synchronization is owned by SurfaceTexture
        float[] producer=new float[16];input.getTransformMatrix(producer);
        float[] rotation=new float[16];Matrix.setIdentityM(rotation,0);
        Matrix.translateM(rotation,0,.5f,.5f,0);Matrix.rotateM(rotation,0,-extraRotation,0,0,1);Matrix.translateM(rotation,0,-.5f,-.5f,0);
        Matrix.multiplyMM(output,0,producer,0,rotation,0);
        // External sampler already returns RGB. Apply no manual YUV matrix here.
    }
}
