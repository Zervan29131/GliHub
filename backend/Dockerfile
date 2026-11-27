FROM maven:3.9-eclipse-temurin-11 AS builder
WORKDIR /build
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

FROM eclipse-temurin:11-jre
WORKDIR /app
COPY --from=builder /build/target/glihub-backend.jar /app/glihub-backend.jar
RUN mkdir -p /app/upload /app/logs /app/ai-outputs
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/glihub-backend.jar"]
