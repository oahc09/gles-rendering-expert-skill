#include "../system_scenes/common.hpp"
int main(int argc,char**argv){try{
 require(argc==3,"fragment and output required");Es30Context ctx;Target out(64,64);
 std::ifstream source(argv[1]);require(bool(source),"shader input");std::string fs((std::istreambuf_iterator<char>(source)),{});
 GLuint p=program("#version 300 es\nprecision highp float;out vec2 uv;void main(){vec2 q=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=q;gl_Position=vec4(q*2.-1.,0,1);}",fs);
 GLuint block=glGetUniformBlockIndex(p,"Film");require(block!=GL_INVALID_INDEX,"missing film block");GLint size;glGetActiveUniformBlockiv(p,block,GL_UNIFORM_BLOCK_DATA_SIZE,&size);require(size==16,"ABI size");
 glUniformBlockBinding(p,block,0);GLuint b;glGenBuffers(1,&b);glBindBuffer(GL_UNIFORM_BUFFER,b);float data[]={1200,1.4,1,0};glBufferData(GL_UNIFORM_BUFFER,sizeof(data),data,GL_STATIC_DRAW);glBindBufferBase(GL_UNIFORM_BUFFER,0,b);
 out.bind();glDisable(GL_DITHER);glUseProgram(p);glDrawArrays(GL_TRIANGLES,0,3);check("film draw");save_ppm(out,argv[2]);
 std::cout<<glGetString(GL_RENDERER)<<"\n"<<glGetString(GL_VERSION)<<"\n";glDeleteBuffers(1,&b);glDeleteProgram(p);
}catch(const std::exception&e){std::cerr<<e.what();return 1;}return 0;}
