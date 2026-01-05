package com.flashsale.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.UUID;

public class SpuDtos {

    public static class SpuCreateDto {
        @NotBlank(message = "Name is required")
        @Size(max = 250, message = "Name must not exceed 250 characters")
        private String name;

        @NotBlank(message = "Slug is required")
        @Size(max = 255, message = "Slug must not exceed 255 characters")
        private String slug;

        private String description;
        private Boolean isActive = true;

        // Constructors
        public SpuCreateDto() {}

        public SpuCreateDto(String name, String slug) {
            this.name = name;
            this.slug = slug;
        }

        // Getters and Setters
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }

        public String getSlug() { return slug; }
        public void setSlug(String slug) { this.slug = slug; }

        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }

        public Boolean getIsActive() { return isActive; }
        public void setIsActive(Boolean isActive) { this.isActive = isActive; }
    }

    public static class SpuUpdateDto {
        @Size(max = 250, message = "Name must not exceed 250 characters")
        private String name;

        @Size(max = 255, message = "Slug must not exceed 255 characters")
        private String slug;

        private String description;
        private Boolean isActive;

        // Constructors
        public SpuUpdateDto() {}

        // Getters and Setters
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }

        public String getSlug() { return slug; }
        public void setSlug(String slug) { this.slug = slug; }

        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }

        public Boolean getIsActive() { return isActive; }
        public void setIsActive(Boolean isActive) { this.isActive = isActive; }
    }

    public static class SpuResponseDto {
        private UUID id;
        private String name;
        private String slug;
        private String description;
        private Boolean isActive;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        // Constructors
        public SpuResponseDto() {}

        // Getters and Setters
        public UUID getId() { return id; }
        public void setId(UUID id) { this.id = id; }

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }

        public String getSlug() { return slug; }
        public void setSlug(String slug) { this.slug = slug; }

        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }

        public Boolean getIsActive() { return isActive; }
        public void setIsActive(Boolean isActive) { this.isActive = isActive; }

        public LocalDateTime getCreatedAt() { return createdAt; }
        public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

        public LocalDateTime getUpdatedAt() { return updatedAt; }
        public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    }
}
