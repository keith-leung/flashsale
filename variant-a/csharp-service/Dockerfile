FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 80

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["FlashSale.Api.csproj", "."]
RUN dotnet restore "FlashSale.Api.csproj"
COPY . .
WORKDIR "/src"
RUN dotnet build "FlashSale.Api.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "FlashSale.Api.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .

# Install netcat for database wait
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Create startup script
RUN echo '#!/bin/sh\n\
TARGET_HOST=${DB_HOST:-10.89.0.2}\n\
echo "Waiting for database at ${TARGET_HOST}:3306..."\n\
while ! nc -z ${TARGET_HOST} 3306; do\n\
  echo "Database not ready yet..."\n\
  sleep 1\n\
done\n\
echo "Database is ready!"\n\
exec dotnet FlashSale.Api.dll' > /app/start.sh && chmod +x /app/start.sh

ENTRYPOINT ["/app/start.sh"]
