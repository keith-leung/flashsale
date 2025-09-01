package com.flashsale.api.controller;

import com.flashsale.api.dto.SkuDtos.*;
import com.flashsale.api.service.SkuService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/skus")
@Tag(name = "SKU Management", description = "Stock Keeping Unit management operations")
public class SkuController {

    private final SkuService skuService;

    @Autowired
    public SkuController(SkuService skuService) {
        this.skuService = skuService;
    }

    @GetMapping
    @Operation(summary = "Get all SKUs", description = "Retrieve a paginated list of all Stock Keeping Units")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved SKUs")
    })
    public ResponseEntity<Page<SkuResponseDto>> getAllSkus(
            @Parameter(description = "Page number (0-based)")
            @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "Page size")
            @RequestParam(defaultValue = "20") int size,
            @Parameter(description = "Filter by SPU ID")
            @RequestParam(required = false) Long spuId) {
        
        Page<SkuResponseDto> skus = skuService.getAllSkus(page, size, spuId);
        return ResponseEntity.ok(skus);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get SKU by ID", description = "Retrieve a specific Stock Keeping Unit by its ID")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved SKU"),
        @ApiResponse(responseCode = "404", description = "SKU not found")
    })
    public ResponseEntity<SkuResponseDto> getSkuById(
            @Parameter(description = "SKU ID")
            @PathVariable Long id) {
        
        return skuService.getSkuById(id)
                .map(sku -> ResponseEntity.ok(sku))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Create new SKU", description = "Create a new Stock Keeping Unit")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Successfully created SKU"),
        @ApiResponse(responseCode = "400", description = "Invalid input or SKU code already exists")
    })
    public ResponseEntity<SkuResponseDto> createSku(
            @Parameter(description = "SKU creation data")
            @Valid @RequestBody SkuCreateDto createDto) {
        
        try {
            SkuResponseDto createdSku = skuService.createSku(createDto);
            return ResponseEntity.status(HttpStatus.CREATED).body(createdSku);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update SKU", description = "Update an existing Stock Keeping Unit")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully updated SKU"),
        @ApiResponse(responseCode = "400", description = "Invalid input or SKU code already exists"),
        @ApiResponse(responseCode = "404", description = "SKU not found")
    })
    public ResponseEntity<SkuResponseDto> updateSku(
            @Parameter(description = "SKU ID")
            @PathVariable Long id,
            @Parameter(description = "SKU update data")
            @Valid @RequestBody SkuUpdateDto updateDto) {
        
        try {
            return skuService.updateSku(id, updateDto)
                    .map(sku -> ResponseEntity.ok(sku))
                    .orElse(ResponseEntity.notFound().build());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete SKU", description = "Delete a Stock Keeping Unit")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "204", description = "Successfully deleted SKU"),
        @ApiResponse(responseCode = "404", description = "SKU not found")
    })
    public ResponseEntity<Void> deleteSku(
            @Parameter(description = "SKU ID")
            @PathVariable Long id) {
        
        if (skuService.deleteSku(id)) {
            return ResponseEntity.noContent().build();
        } else {
            return ResponseEntity.notFound().build();
        }
    }
}
