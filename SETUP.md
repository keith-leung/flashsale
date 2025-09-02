# Gradual Setup Guide for the Flash Sale System in a Dedicated WSL Instance

This guide provides a comprehensive, **gradual, and upgradable** setup for testing the Flash Sale system. To ensure a clean and isolated environment, we will begin by creating a dedicated **Ubuntu 24.04 LTS** instance in WSL named `flash-sale`.

We will then proceed in phases, starting with a **simple prototype** using a non-optimized, database-centric approach with your existing services (Java 21+, Python 3.11+, .NET 8+) and MySQL 8+. After establishing a baseline, we'll upgrade step-by-step to incorporate the "golden solution" components (Redis Cluster, in-memory pools, Kafka), allowing for clear performance comparison at each stage.

**Key Goals:**
- **Isolated Environment:** Use a custom-named WSL instance to avoid conflicts.
- **Phase-Based Deployment:** Start simple and add complexity gradually.
- **Performance Benchmarking:** Compare the ordinary solution against the golden solution.
- **Technology Stack:** Utilize Podman for containerization within the dedicated WSL environment.

---

## Section 1: Setting Up the Dedicated `flash-sale` WSL Instance

This section details how to create a clean, custom-named WSL instance for this project.

### 1.1: Ensure WSL 2 is Enabled
- Open PowerShell as Administrator.
- Verify WSL status: `wsl --list --verbose` (or `wsl -l -v`). Ensure you see `VERSION 2` for any existing instances.
- If WSL isn't installed, run `wsl --install` and restart your machine.

### 1.2: Create a Custom Ubuntu 24.04 Instance
We will install the standard Ubuntu 24.04, export it, and then re-import it with a custom name and location.

1.  **Install Ubuntu 24.04 from Microsoft Store:**
    - Check available distributions: `wsl --list --online`.
    - Install the base image: `wsl --install -d Ubuntu-24.04`. This creates a default instance we will use as a template.

2.  **Export the Base Image:**
    - Create a dedicated folder on your Windows drive for WSL data: `mkdir C:\WSL`.
    - Export the newly installed instance to a `.tar` file:
      ```powershell
      wsl --export Ubuntu-24.04 C:\WSL\ubuntu-24.04.tar
      ```

3.  **Import as a Custom Instance:**
    - Create a directory to store the virtual disk for your new instance: `mkdir C:\WSL\flash-sale`.
    - Import the exported image with the name `flash-sale`:
      ```powershell
      wsl --import flash-sale C:\WSL\flash-sale C:\WSL\ubuntu-24.04.tar --version 2
      ```

4.  **Verify and Clean Up:**
    - List your WSL instances to confirm success: `wsl -l -v`. You should see `flash-sale` listed.
    - (Optional) To save space, you can now remove the original `Ubuntu-24.04` instance:
      ```powershell
      wsl --unregister Ubuntu-24.04
      ```
    - (Optional) You may also delete the exported archive: `del C:\WSL\ubuntu-24.04.tar`.

### 1.3: Initialize and Configure the `flash-sale` Instance
1.  **Launch the new instance:**
    ```powershell
    wsl -d flash-sale
    ```
2.  **Create a User Account:** On the first launch, you will be prompted to create a default UNIX user account. This user will have `sudo` privileges.
3.  **Update Packages:**
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```
4.  **Install All Project Dependencies:** Run the following command block to install Podman, language runtimes, and other essential tools:
    ```bash
    # Install Podman, container tools, and networking utilities
    sudo apt install -y podman podman-compose curl git build-essential net-tools iputils-ping tcpdump iptables mysql-client

    # Install Java 21+
    sudo apt install -y openjdk-21-jdk

    # Install .NET 8 SDK
    sudo apt install -y dotnet-sdk-8.0

    # Install Miniconda for Python 3.11+ environment management
    curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
    # Follow the prompt to initialize conda, or run:
    $HOME/miniconda3/bin/conda init
    # Close and reopen your WSL terminal for conda to be available in your PATH
    ```
5.  **Set up Python Environment (New Terminal):**
    - After reopening your terminal, create and activate a conda environment:
    ```bash
    conda create -n flashenv python=3.11
    conda activate flashenv
    ```
6.  **Configure Podman:**
    - Initialize Podman's storage and enable user services to run on boot:
    ```bash
    podman system migrate
    loginctl enable-linger $USER
    ```

### 1.4: Project Directory Setup
Inside your `flash-sale` WSL instance, create the project structure.

```bash
# In your WSL terminal (e.g., /home/your_user/)
mkdir -p ~/flash-sale-setup/services
cd ~/flash-sale-setup

# Create directories for persistent container data
mkdir -p volumes/{mysql,postgres,redis1,redis2,redis3,kafka1,kafka2,kafka3,zookeeper,logs}

# Clone or copy your service codebases into the 'services' directory
# For example:
# git clone <your-java-repo> services/java-app
```
---

## Section 2: Setting Up WSL

1. **Enable WSL on Windows:**
   - Open PowerShell as Administrator.
   - Run: `wsl --install` (installs Ubuntu by default and enables WSL 2).
   - Restart your machine if prompted.
   - Verify: `wsl -l -v` (should show Ubuntu running on WSL 2).

2. **Install/Launch Ubuntu in WSL:**
   - Launch Ubuntu from the Start menu or run `wsl` in PowerShell.
   - Set up a username and password when prompted.
   - Update packages: `sudo apt update && sudo apt upgrade -y`.

3. **Install Essential Tools in WSL:**
   - `sudo apt install -y curl git build-essential net-tools iputils-ping tcpdump iptables`.

## Section 3: Installing Podman in WSL

Podman is preferred over Docker for WSL due to its daemonless nature (no root daemon issues).

1. **Install Podman:**
   - In WSL Ubuntu: `sudo apt install -y podman`.
   - Verify: `podman --version` (should be 3.4+).

2. **Install Podman Compose (for Docker Compose-like functionality):**
   - `sudo apt install -y podman-compose` (or use `pip install podman-compose` if needed).
   - Note: Podman Compose emulates `docker-compose` syntax.

3. **Configure Podman for Rootless Operation:**
   - Run `podman system migrate` to initialize.
   - Enable lingering for user namespaces: `loginctl enable-linger $USER`.
   - Test: `podman run hello-world` (pulls and runs a test image).

4. **Handle WSL Networking Quirks:**
   - WSL uses a virtual network. To access container ports from Windows, use `localhost` forwarding.
   - Install `socat` for port forwarding if needed: `sudo apt install -y socat`.

## Section 4: Configuring Services with Podman

We'll define services based on the architecture:
- **PostgreSQL:** Database for orders (async writes).
- **Redis Cluster:** For pub/sub, shared inventory (3 nodes as per YAML).
- **Kafka Cluster:** For async order creation (3 nodes + Zookeeper).
- **Filebeat:** For shipping logs to Kafka.
- **Saleor App Instances:** 3 instances to simulate multi-tier (with custom flash sale code).
- **Monitoring (Prometheus + Grafana):** For metrics and health checks.

Use Podman Compose YAML files for orchestration.

### 4.1: Create Project Directory
In WSL: 
```
mkdir -p ~/flash-sale-setup
cd ~/flash-sale-setup
mkdir -p volumes/{postgres,redis1,redis2,redis3,kafka1,kafka2,kafka3,zookeeper,logs}
```

### 4.2: Redis Cluster Compose File
Save as `redis-compose.yaml` (adapted from provided YAML):

```yaml
version: '3.8'
services:
  redis-node-1:
    image: redis:7-alpine
    container_name: redis-node-1
    ports:
      - "7000:7000"
    volumes:
      - ./volumes/redis1-data:/data
    command: >
      redis-server
      --port 7000
      --cluster-enabled yes
      --cluster-config-file nodes.conf
      --cluster-node-timeout 5000
      --appendonly yes
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
    networks:
      - flash-net

  redis-node-2:
    image: redis:7-alpine
    container_name: redis-node-2
    ports:
      - "7001:7001"
    volumes:
      - ./volumes/redis2-data:/data
    command: >
      redis-server
      --port 7001
      --cluster-enabled yes
      --cluster-config-file nodes.conf
      --cluster-node-timeout 5000
      --appendonly yes
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
    networks:
      - flash-net

  redis-node-3:
    image: redis:7-alpine
    container_name: redis-node-3
    ports:
      - "7002:7002"
    volumes:
      - ./volumes/redis3-data:/data
    command: >
      redis-server
      --port 7002
      --cluster-enabled yes
      --cluster-config-file nodes.conf
      --cluster-node-timeout 5000
      --appendonly yes
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Start: `podman-compose -f redis-compose.yaml up -d`.
- Initialize cluster: `podman exec -it redis-node-1 redis-cli --cluster create 127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 --cluster-replicas 0`.

### 4.3: Kafka Cluster Compose File
Save as `kafka-compose.yaml` (basic 3-node setup with Zookeeper):

```yaml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.0.1
    container_name: zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - ./volumes/zookeeper:/var/lib/zookeeper/data
    networks:
      - flash-net
    ports:
      - "2181:2181"

  kafka1:
    image: confluentinc/cp-kafka:7.0.1
    container_name: kafka1
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka1:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    volumes:
      - ./volumes/kafka1:/var/lib/kafka/data
    networks:
      - flash-net

  kafka2:
    image: confluentinc/cp-kafka:7.0.1
    container_name: kafka2
    depends_on:
      - zookeeper
    ports:
      - "9093:9093"
    environment:
      KAFKA_BROKER_ID: 2
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka2:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    volumes:
      - ./volumes/kafka2:/var/lib/kafka/data
    networks:
      - flash-net

  kafka3:
    image: confluentinc/cp-kafka:7.0.1
    container_name: kafka3
    depends_on:
      - zookeeper
    ports:
      - "9094:9094"
    environment:
      KAFKA_BROKER_ID: 3
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka3:9094
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    volumes:
      - ./volumes/kafka3:/var/lib/kafka/data
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Start: `podman-compose -f kafka-compose.yaml up -d`.
- Create topic: `podman exec -it kafka1 kafka-topics --create --topic flash_sale_orders --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1`.

### 4.4: PostgreSQL Compose File
Save as `postgres-compose.yaml`:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:14
    container_name: postgres
    environment:
      POSTGRES_DB: saleor
      POSTGRES_USER: saleor
      POSTGRES_PASSWORD: saleor
    volumes:
      - ./volumes/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Start: `podman-compose -f postgres-compose.yaml up -d`.

### 4.5: Filebeat Compose File
Save as `filebeat-compose.yaml`. Mount your `filebeat.yml` (from the code) as a volume.

```yaml
version: '3.8'
services:
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.0.0
    container_name: filebeat
    user: root
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - ./volumes/logs:/var/log/flash_sale_orders:ro  # Mount log dir
    environment:
      - -strict.perms=false
    networks:
      - flash-net
    depends_on:
      - kafka1
      - kafka2
      - kafka3

networks:
  flash-net:
    driver: bridge
```

- Create `filebeat.yml` in the project dir with the provided YAML content.
- Start: `podman-compose -f filebeat-compose.yaml up -d`.

### 4.6: Saleor App Instances Compose File
Build a custom Saleor image with your code. First, create a `Dockerfile` in the Saleor repo:

```dockerfile
FROM python:3.9
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt  # Assuming Saleor setup
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

Build: `podman build -t custom-saleor .` (from Saleor dir).

Then, save as `saleor-compose.yaml` (3 instances for simulation):

```yaml
version: '3.8'
services:
  saleor-instance-1:
    image: custom-saleor
    container_name: saleor-1
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://saleor:saleor@postgres:5432/saleor
      REDIS_URL: redis://redis-node-1:7000  # Connect to Redis cluster
      KAFKA_BOOTSTRAP_SERVERS: kafka1:9092,kafka2:9093,kafka3:9094
      INSTANCE_ID: instance1
    volumes:
      - ./saleor-custom-code:/app/saleor/flash_sale  # Mount custom code
    depends_on:
      - postgres
      - redis-node-1
      - kafka1
    networks:
      - flash-net

  saleor-instance-2:
    image: custom-saleor
    container_name: saleor-2
    ports:
      - "8001:8000"
    environment:
      DATABASE_URL: postgres://saleor:saleor@postgres:5432/saleor
      REDIS_URL: redis://redis-node-1:7000
      KAFKA_BOOTSTRAP_SERVERS: kafka1:9092,kafka2:9093,kafka3:9094
      INSTANCE_ID: instance2
    volumes:
      - ./saleor-custom-code:/app/saleor/flash_sale
    depends_on:
      - postgres
      - redis-node-1
      - kafka1
    networks:
      - flash-net

  saleor-instance-3:
    image: custom-saleor
    container_name: saleor-3
    ports:
      - "8002:8000"
    environment:
      DATABASE_URL: postgres://saleor:saleor@postgres:5432/saleor
      REDIS_URL: redis://redis-node-1:7000
      KAFKA_BOOTSTRAP_SERVERS: kafka1:9092,kafka2:9093,kafka3:9094
      INSTANCE_ID: instance3
    volumes:
      - ./saleor-custom-code:/app/saleor/flash_sale
    depends_on:
      - postgres
      - redis-node-1
      - kafka1
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Start: `podman-compose -f saleor-compose.yaml up -d`.
- Migrate DB: `podman exec -it saleor-1 python manage.py migrate`.

### 4.7: Monitoring Compose File (Optional)
Save as `monitoring-compose.yaml` for Prometheus + Grafana.

```yaml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - flash-net

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Create `prometheus.yml` with scrapes for your metrics endpoints.
- Start: `podman-compose -f monitoring-compose.yaml up -d`.

## Section 5: Emulating Network Saturation

To test network saturation (e.g., for Redis pub/sub bandwidth exhaustion), use `tc` inside containers or on the Podman network.

1. **Install tc in Containers (if needed):**
   - For Redis/Saleor containers, add `RUN apt install -y iproute2` to Dockerfile and rebuild.

2. **Apply Network Limits to a Container (e.g., Simulate Saturation on Redis Node 1):**
   - Enter container: `podman exec -it redis-node-1 /bin/sh`.
   - Limit bandwidth to 1Mbps with 50ms delay and 5% packet loss:
     ```
     tc qdisc add dev eth0 root handle 1: tbf rate 1mbit burst 32kbit latency 400ms
     tc qdisc add dev eth0 parent 1:1 handle 10: netem delay 50ms loss 5%
     ```
   - Verify: `tc qdisc show dev eth0`.
   - Remove: `tc qdisc del dev eth0 root`.

3. **Emulate on Podman Network (Global):**
   - Create a custom network with limits: Podman doesn't natively support tc on bridges, so use host-level tc on WSL's veth interfaces.
   - List interfaces: `ip link show`.
   - Apply to a veth (e.g., veth0 for flash-net): `sudo tc qdisc add dev veth0 root tbf rate 10mbit burst 32kbit latency 100ms`.

4. **Test Scenarios:**
   - **Bandwidth Exhaustion:** Set low rate (e.g., 1mbit) on Redis interfaces to simulate LAN exhaustion.
   - **Latency for Pub/Sub:** Add 100ms delay to test sync timing.
   - **Packet Loss:** 10% loss to emulate race conditions.
   - Use tools like `iperf` (install: `sudo apt install iperf`) to measure: Run server in one container, client in another.

5. **Automate with Scripts:**
   - Create a script `emulate_saturation.sh`:
     ```bash
     #!/bin/bash
     CONTAINER=$1
     RATE=$2  # e.g., 1mbit
     DELAY=$3  # e.g., 50ms
     LOSS=$4   # e.g., 5%
     podman exec -it $CONTAINER tc qdisc add dev eth0 root tbf rate $RATE burst 32kbit latency 400ms
     podman exec -it $CONTAINER tc qdisc add dev eth0 parent 1: netem delay $DELAY loss $LOSS
     ```
   - Usage: `./emulate_saturation.sh redis-node-1 1mbit 50ms 5%`.

## Section 6: Running and Testing

1. **Start All Services:**
   - Run each compose file with `podman-compose up -d`.
   - Verify: `podman ps` (all containers running).

2. **Initialize Data:**
   - Pre-allocate inventory: Use the provided Python code via `podman exec saleor-1 python manage.py shell`.
   - Test API: From Windows, curl `http://localhost:8000/api/flash-sale/status/` (forward ports if needed).

3. **Load Testing:**
   - Use the provided `locustfile.py`: Install Locust in WSL (`pip install locust`), run `locust -f locustfile.py`.
   - Emulate 100k users: `--users=10000 --spawn-rate=1000`.
   - Monitor with Grafana (localhost:3000).

4. **Emulate Saturation During Tests:**
   - Apply tc limits, run Locust, observe failures (e.g., overselling if sync fails).

## Section 7: Troubleshooting

- **Podman Issues:** Check logs `podman logs <container>`. Restart with `podman-compose down && up -d`.
- **Networking:** If ports not accessible from Windows, use `socat tcp-listen:8000,fork,reuseaddr tcp:127.0.0.1:8000` in WSL.
- **tc Not Working:** Ensure container has `iproute2` and run as root.
- **Performance:** WSL has overhead; for real tests, use native Linux.
- **Errors:** For Qt bindings (from initial query), ensure no GUI deps in containers.
- **Cleanup:** `podman-compose down -v` to remove volumes.





# Gradual Setup Guide for Flash Sale System in WSL with Podman

Based on your request, I'll redesign the setup to be **gradual and upgradable**. We'll start with a **simple prototype** using a non-optimized, database-centric flash sale system (ordinary approach with direct MySQL contention, as critiqued in the golden solution). This will use MySQL 8+ as the primary database, with your mentioned implementations (Java 21+, Python 3.11+ via conda/venv, .NET 8+). After validating this baseline, we'll upgrade step-by-step to incorporate elements of the "golden solution" (e.g., Redis for pub/sub and shared inventory, in-memory pools, Kafka for async orders). This allows performance comparison at each stage.

**Assumptions:**
- Your services are microservices or apps in Java, Python, and .NET that handle flash sale logic (e.g., Java for backend API, Python for inventory service, .NET for order processing). If not, adapt the examples accordingly.
- We'll use Podman for containerization to keep it isolated and scalable.
- Focus on WSL (Ubuntu) as before.
- Performance testing: Use tools like Locust (from the original locustfile.py) or JMeter for load tests at each phase.
- Database: Start with MySQL 8+, then optionally migrate to PostgreSQL for golden compatibility.
- Gradual means: Each phase builds on the previous (e.g., add services without tearing down the whole setup).

**Prerequisites (Same as Before):**
- WSL 2 with Ubuntu installed.
- Podman and Podman Compose installed (see previous guide).
- Your codebases for Java/Python/.NET services ready (e.g., cloned in `~/flash-sale-setup/services/`).
- MySQL client tools: `sudo apt install -y mysql-client`.

Create a project dir: `mkdir -p ~/flash-sale-setup && cd ~/flash-sale-setup`.

## Phase 1: Simple Prototype (Non-Optimized, Database-Centric with MySQL)

Goal: Validate a basic flash sale system using ordinary database reads/writes (e.g., read-check-write pattern that fails at scale, as per the problem analysis). No Redis/Kafka/in-memory pools yet. Use MySQL for all data (inventory, orders).

### 1.1: Set Up MySQL Container
Save as `mysql-compose.yaml`:

```yaml
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    container_name: mysql
    environment:
      MYSQL_DATABASE: flashsale
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_USER: user
      MYSQL_PASSWORD: pass
    volumes:
      - ./volumes/mysql:/var/lib/mysql
    ports:
      - "3306:3306"
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Start: `podman-compose -f mysql-compose.yaml up -d`.
- Initialize DB: Connect via `podman exec -it mysql mysql -u root -prootpass`, then create tables (e.g., `CREATE TABLE inventory (id INT PRIMARY KEY, stock INT); INSERT INTO inventory VALUES (1, 1000);` for basic testing).

### 1.2: Containerize Your Services
Build custom images for each language. Place your code in subdirs (e.g., `services/java-app/`, `services/python-app/`, `services/dotnet-app/`).

- **Java 21+ Service (e.g., API Server):**
  Dockerfile in `services/java-app/`:
  ```dockerfile
  FROM openjdk:21-jdk
  WORKDIR /app
  COPY . /app
  RUN ./gradlew build  # Or mvn package if using Maven
  CMD ["java", "-jar", "build/libs/your-app.jar"]
  ```
  Build: `podman build -t java-flash-service .` (from dir).

- **Python 3.11+ Service (e.g., Inventory Handler):**
  Use conda/venv in Dockerfile for env management.
  Dockerfile in `services/python-app/`:
  ```dockerfile
  FROM continuumio/miniconda3
  WORKDIR /app
  COPY . /app
  RUN conda create -n flashenv python=3.11 && \
      conda run -n flashenv pip install -r requirements.txt
  CMD ["conda", "run", "-n", "flashenv", "python", "app.py"]
  ```
  Build: `podman build -t python-flash-service .`.

- **.NET 8+ Service (e.g., Order Processor):**
  Dockerfile in `services/dotnet-app/`:
  ```dockerfile
  FROM mcr.microsoft.com/dotnet/aspnet:8.0
  WORKDIR /app
  COPY . /app
  RUN dotnet publish -c Release -o out
  ENTRYPOINT ["dotnet", "out/your-app.dll"]
  ```
  Build: `podman build -t dotnet-flash-service .`.

### 1.3: Compose File for Services
Save as `phase1-services-compose.yaml`:

```yaml
version: '3.8'
services:
  java-service:
    image: java-flash-service
    container_name: java-service
    ports:
      - "8080:8080"  # Adjust port
    environment:
      DB_URL: jdbc:mysql://mysql:3306/flashsale?user=user&password=pass
    depends_on:
      - mysql
    networks:
      - flash-net

  python-service:
    image: python-flash-service
    container_name: python-service
    ports:
      - "5000:5000"  # Adjust
    environment:
      DB_URL: mysql://user:pass@mysql:3306/flashsale
    depends_on:
      - mysql
    networks:
      - flash-net

  dotnet-service:
    image: dotnet-flash-service
    container_name: dotnet-service
    ports:
      - "5001:80"  # Adjust
    environment:
      ConnectionStrings__Default: Server=mysql;Database=flashsale;User=user;Password=pass;
    depends_on:
      - mysql
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Start: `podman-compose -f phase1-services-compose.yaml up -d`.
- Implement Ordinary Logic: In your code, use direct DB transactions (e.g., in Python: use SQLAlchemy for `@transaction.atomic` with read-check-write, as in the failing example).

### 1.4: Validation and Testing
- **Basic Test:** Curl endpoints (e.g., `curl http://localhost:8080/flash-sale/reserve` to simulate reservations).
- **Load Test:** Adapt locustfile.py to your endpoints. Run `locust` in WSL, target 100-1000 concurrent users. Expect failures at scale (e.g., overselling due to race conditions).
- **Metrics:** Use built-in tools (e.g., MySQL `SHOW STATUS LIKE 'Threads_running';`) to monitor contention.
- **Emulate Saturation:** Apply `tc` limits to mysql container (see previous guide, e.g., limit bandwidth to 10mbit).

Once validated (e.g., works for low traffic but fails under load), proceed.

## Phase 2: Add Redis for Basic Caching and Pub/Sub (Intermediate Optimization)

Goal: Introduce Redis to reduce some DB contention (e.g., cache inventory counts, use pub/sub for simple sync). Compare performance to Phase 1.

### 2.1: Add Redis (Single Node for Simplicity)
Save as `redis-simple-compose.yaml`:

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    networks:
      - flash-net

networks:
  flash-net:
    driver: bridge
```

- Start: `podman-compose -f redis-simple-compose.yaml up -d` (builds on existing network).

### 2.2: Update Services
- Update Dockerfiles/environments to connect to Redis (e.g., Python: install `redis` lib; Java: Jedis; .NET: StackExchange.Redis).
- Implement: Use Redis for caching (e.g., store inventory in Redis with TTL), basic pub/sub for invalidation.
- Restart services: `podman-compose -f phase1-services-compose.yaml down && up -d`.

### 2.3: Performance Comparison
- Rerun load tests from Phase 1.
- Expect: Better than Phase 1 (e.g., 2-5x throughput) but still limited (e.g., Redis becomes bottleneck at 10k+ users).
- Metrics: Monitor Redis CPU/network with `podman exec redis redis-cli INFO`.

## Phase 3: Upgrade to Redis Cluster and In-Memory Pools (Core Golden Features)

Goal: Implement pre-allocated memory pools (local 70%/shared 30%), Redis cluster for sync. This tests the "golden" outperform claim.

### 3.1: Replace Simple Redis with Cluster
Use the `redis-compose.yaml` from the original guide (3 nodes). Start it, initialize cluster.

### 3.2: Integrate Golden Code
- In your Python service (assuming it handles inventory): Add the provided `InMemoryInventoryPool`, `PreAllocationStrategy`, etc.
- For Java/.NET: Port equivalent logic (e.g., use Caffeine for local caches, Lettuce for Redis cluster).
- Update env: `REDIS_CLUSTER_NODES=redis-node-1:7000,redis-node-2:7001,redis-node-3:7002`.
- Restart services.

### 3.3: Testing and Comparison
- Implement hybrid reserve (local pool first, then shared Redis).
- Load Test: Scale to 10k+ users. Compare metrics (e.g., response time, overselling rate) to Phase 2.
- Emulate Saturation: Limit Redis network to test pub/sub resilience.

## Phase 4: Add Kafka for Async Order Creation (Full Golden Solution)

Goal: Eliminate DB writes from critical path.

### 4.1: Add Kafka and Filebeat
Use `kafka-compose.yaml` and `filebeat-compose.yaml` from original guide. Start them.

### 4.2: Integrate Async Logic
- In services: Add Snowflake ID generator, local logging buffer, Kafka producers/consumers (e.g., Python: confluent-kafka; Java: Kafka clients; .NET: Confluent.Kafka).
- Update order flow: Queue to logs → Filebeat → Kafka → Batch DB insert.
- For consumers: Run as separate containers (e.g., add to compose).

### 4.3: Full Testing
- Load Test: Aim for 100k simulated users. Measure end-to-end (e.g., 1ms confirmations).
- Comparison: Quantify speedup (e.g., throughput 10-20x Phase 1).
- Migrate DB: If needed, switch MySQL to PostgreSQL by updating compose and migrating data (`mysqldump` → `psql`).

## Phase 5: Monitoring and Final Optimizations
- Add `monitoring-compose.yaml` from original.
- Integrate provided metrics (e.g., Prometheus exporters in services).
- Scale: Add more service instances (e.g., duplicate in compose).
- Gradual Teardown: Stop/add components via individual compose files.
