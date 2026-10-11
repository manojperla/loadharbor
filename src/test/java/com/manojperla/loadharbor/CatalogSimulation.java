package com.manojperla.loadharbor;
import io.gatling.javaapi.core.*;
import java.nio.file.Path;
import java.time.Duration;
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class CatalogSimulation extends Simulation {
    private final Telemetry telemetry;
    private ChainBuilder measured(String name,String path) {
        return exec(s->s.markAsSucceeded().remove("responseMs").set("startedNs",System.nanoTime()))
            .exec(http(name).get(path).requestTimeout(Duration.ofSeconds(10)).check(responseTimeInMillis().saveAs("responseMs"),status().is(200),jsonPath("$.ok").ofBoolean().is(true)))
            .exec(s->{
                long ms=s.contains("responseMs")?((Number)s.get("responseMs")).longValue():(System.nanoTime()-s.getLong("startedNs"))/1000000;
                telemetry.record(name,ms,s.isFailed());return s;
            });
    }
    public CatalogSimulation() throws Exception {
        String profile=System.getProperty("profile","smoke");
        int seconds=Integer.parseInt(System.getProperty("duration","10"));
        double rate=Double.parseDouble(System.getProperty("rate","1"));
        int p95=Integer.parseInt(System.getProperty("p95Ms","1000"));
        double errors=Double.parseDouble(System.getProperty("maxErrorPercent","1"));
        if(seconds<1 || seconds>3600 || !Double.isFinite(rate) || rate<=0 || rate>100 || p95<1 || !Double.isFinite(errors) || errors<0 || errors>100) throw new IllegalArgumentException("Invalid load or threshold configuration");
        telemetry=new Telemetry(Path.of(System.getProperty("telemetry",".run/events.tsv")),profile);
        var scenario=scenario("Browse catalog")
            .exec(measured("catalog","/api/products")).pause(Duration.ofMillis(100))
            .exec(measured("product","/api/products/1")).pause(Duration.ofMillis(100))
            .exec(measured("search","/api/search?q=book"));
        var protocol=http.baseUrl(System.getProperty("baseUrl","http://127.0.0.1:8089"))
            .acceptHeader("application/json").disableCaching();
        var injection=profile.equals("stress")?rampUsersPerSec(1).to(rate).during(seconds):constantUsersPerSec(rate).during(seconds);
        setUp(scenario.injectOpen(injection)).protocols(protocol)
            .assertions(global().responseTime().percentile(95.0).lte(p95),global().failedRequests().percent().lte(errors),global().allRequests().count().gte(1L));
    }
    @Override public void after() { telemetry.close(); }
}
