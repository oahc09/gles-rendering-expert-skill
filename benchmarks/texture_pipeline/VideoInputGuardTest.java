package org.example.gleslab;
/** Host JVM tests of fail-closed branches only. No GLES/Android method is executed. */
public final class VideoInputGuardTest {
    private static void check(boolean value){if(!value)throw new AssertionError();}
    public static void main(String[] args){
        check(VideoInputGuard.select(true,"RGB","full","SDR").equals("BLOCKED_PROTECTED_PIPELINE"));
        check(VideoInputGuard.select(false,"unknown","limited","SDR").equals("BLOCKED_UNKNOWN_COLOR"));
        check(VideoInputGuard.select(false,"BT709","unknown","SDR").equals("BLOCKED_UNKNOWN_COLOR"));
        check(VideoInputGuard.select(false,"BT2020","limited","PQ").equals("BLOCKED_HDR_TONEMAP_REQUIRED"));
        check(VideoInputGuard.select(false,null,"full","SDR").equals("BLOCKED_UNKNOWN_COLOR"));
        boolean rejected=false;
        try{VideoInputGuard.acquireFrame(null,new float[16],90,true);}catch(IllegalArgumentException expected){rejected=true;}
        check(rejected);rejected=false;
        try{VideoInputGuard.acquireFrame(null,new float[16],45,false);}catch(IllegalArgumentException expected){rejected=true;}
        check(rejected);System.out.println("PASS 7 host guard assertions; GL/Android runtime NOT_RUN");
    }
}
