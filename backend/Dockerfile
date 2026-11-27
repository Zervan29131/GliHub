# GliHub 3.0 Spring Boot 4.2 + OpenJDK 25 LTS Multi-Arch Image
FROM eclipse-temurin:25-jdk-noble AS builder
WORKDIR /build
COPY mvnw pom.xml ./
COPY .mvn .mvn
RUN chmod +x mvnw && ./mvnw dependency:go-offline -B
COPY src src
RUN ./mvnw clean package -DskipTests -B

FROM eclipse-temurin:25-jre-noble
ENV TZ=Asia/Shanghai \
    JAVA_OPTS="-XX:+IgnoreUnrecognizedVMOptions -XX:+UseCompactObjectHeaders -XX:+UseZGC -Xms256m -Xmx768m"
WORKDIR /app
COPY --from=builder /build/target/glihub-backend.jar /app/glihub-backend.jar
RUN mkdir -p /data/uploads /data/models /data/edge_snaps

EXPOSE 8080

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/glihub-backend.jar"]
