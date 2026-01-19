FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy project files
COPY FlashSale.csproj .
RUN dotnet restore "FlashSale.csproj"

# Copy all other files
COPY . .

# Build and publish
WORKDIR "/src"
RUN dotnet build "FlashSale.csproj" -c Release -o /app/build
RUN dotnet publish "FlashSale.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

# Copy published files
COPY --from=build /app/publish .

# Set environment variables
ENV ASPNETCORE_URLS=http://+:80
ENV ASPNETCORE_ENVIRONMENT=Production

# Expose port
EXPOSE 80

# Start application
ENTRYPOINT ["dotnet", "FlashSale.dll"]