FROM eclipse-temurin:21-jdk

WORKDIR /app

# Install Maven
RUN apt-get update && apt-get install -y maven && rm -rf /var/lib/apt/lists/*

# Copy pom.xml first for better caching
COPY pom.xml ./

# Download dependencies
RUN mvn dependency:go-offline -B || true

# Copy source code
COPY src src

# Build the application
RUN mvn clean package -DskipTests

# Expose port
EXPOSE 8080

# Add wait-for-it script for database readiness
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Create startup script
RUN echo '#!/bin/sh\n\
DB_HOST=${DB_HOST:-flash-mariadb}\n\
echo "Waiting for database at ${DB_HOST}:3306..."\n\
while ! nc -z ${DB_HOST} 3306; do\n\
  sleep 1\n\
done\n\
echo "Database is ready!"\n\
exec java -jar target/flashsale-api-0.0.1-SNAPSHOT.jar' > /app/start.sh && chmod +x /app/start.sh

# Run the application
CMD ["/app/start.sh"]
