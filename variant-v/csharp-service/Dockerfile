FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine AS base
WORKDIR /app
EXPOSE 30016

FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS build
WORKDIR /src
COPY ["FlashSale.Api.V.csproj", "."]
RUN dotnet restore "./FlashSale.Api.V.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "FlashSale.Api.V.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "FlashSale.Api.V.csproj" -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "FlashSale.Api.V.dll"]
