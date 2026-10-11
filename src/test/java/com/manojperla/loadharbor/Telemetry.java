package com.manojperla.loadharbor;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/** Application-owned event format; never parses or extends Gatling internals. */
final class Telemetry implements AutoCloseable {
    private final BlockingQueue<String> queue = new ArrayBlockingQueue<>(100000);
    private final AtomicReference<Throwable> failure = new AtomicReference<>();
    private final Thread writer;
    private volatile boolean done;
    Telemetry(Path file, String profile) throws IOException {
        Files.createDirectories(file.toAbsolutePath().getParent());
        BufferedWriter out=Files.newBufferedWriter(file,StandardCharsets.UTF_8);
        out.write("RUN\t"+System.currentTimeMillis()+"\t"+profile+"\n"); out.flush();
        writer=new Thread(()->{
            try(out) {
                while(!done || !queue.isEmpty()) {
                    String line=queue.poll(100,TimeUnit.MILLISECONDS);
                    if(line!=null) {out.write(line);out.newLine();}
                    if(queue.isEmpty()) out.flush();
                }
                out.write("DONE\n");out.flush();
            } catch(Exception e) { failure.set(e); }
        },"loadharbor-telemetry");
        writer.setDaemon(true);writer.start();
    }
    void record(String name,long duration,boolean failed) {
        if(!queue.offer("REQUEST\t"+name+"\t"+duration+"\t"+(failed?"KO":"OK")))
            failure.compareAndSet(null,new IllegalStateException("Telemetry queue overflow"));
    }
    public void close() {
        done=true;
        try {writer.join(10000);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new RuntimeException(e);}
        if(writer.isAlive()) throw new IllegalStateException("Telemetry writer did not finish");
        if(failure.get()!=null) throw new IllegalStateException("Telemetry incomplete",failure.get());
    }
}
