package com.flashsale.api.controller;

import com.flashsale.api.dto.InventoryDtos.*;
import com.flashsale.api.service.InventoryService;
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
@RequestMapping("/api/v1/inventory")
@Tag(name = "Inventory Management", description = "Inventory management operations")
public class InventoryController {

    private final InventoryService inventoryService;

    @Autowired
    public InventoryController(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    @GetMapping
    @Operation(summary = "Get all inventory records", description = "Retrieve a paginated list of all inventory records")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved inventory records")
    })
    public ResponseEntity<Page<InventoryResponseDto>> getAllInventory(
            @Parameter(description = "Page number (0-based)")
            @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "Page size")
            @RequestParam(defaultValue = "20") int size,
            @Parameter(description = "Filter by SKU ID")
            @RequestParam(required = false) Long skuId) {
        
        Page<InventoryResponseDto> inventory = inventoryService.getAllInventory(page, size, skuId);
        return ResponseEntity.ok(inventory);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get inventory by ID", description = "Retrieve a specific inventory record by its ID")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved inventory record"),
        @ApiResponse(responseCode = "404", description = "Inventory record not found")
    })
    public ResponseEntity<InventoryResponseDto> getInventoryById(
            @Parameter(description = "Inventory ID")
            @PathVariable Long id) {
        
        return inventoryService.getInventoryById(id)
                .map(inventory -> ResponseEntity.ok(inventory))
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/sku/{skuId}")
    @Operation(summary = "Get inventory by SKU ID", description = "Retrieve inventory record for a specific SKU")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved inventory record"),
        @ApiResponse(responseCode = "404", description = "Inventory record not found")
    })
    public ResponseEntity<InventoryResponseDto> getInventoryBySkuId(
            @Parameter(description = "SKU ID")
            @PathVariable Long skuId) {
        
        return inventoryService.getInventoryBySkuId(skuId)
                .map(inventory -> ResponseEntity.ok(inventory))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Create new inventory record", description = "Create a new inventory record")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Successfully created inventory record"),
        @ApiResponse(responseCode = "400", description = "Invalid input or inventory already exists for SKU")
    })
    public ResponseEntity<InventoryResponseDto> createInventory(
            @Parameter(description = "Inventory creation data")
            @Valid @RequestBody InventoryCreateDto createDto) {
        
        try {
            InventoryResponseDto createdInventory = inventoryService.createInventory(createDto);
            return ResponseEntity.status(HttpStatus.CREATED).body(createdInventory);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update inventory record", description = "Update an existing inventory record")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully updated inventory record"),
        @ApiResponse(responseCode = "400", description = "Invalid input"),
        @ApiResponse(responseCode = "404", description = "Inventory record not found")
    })
    public ResponseEntity<InventoryResponseDto> updateInventory(
            @Parameter(description = "Inventory ID")
            @PathVariable Long id,
            @Parameter(description = "Inventory update data")
            @Valid @RequestBody InventoryUpdateDto updateDto) {
        
        try {
            return inventoryService.updateInventory(id, updateDto)
                    .map(inventory -> ResponseEntity.ok(inventory))
                    .orElse(ResponseEntity.notFound().build());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete inventory record", description = "Delete an inventory record")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "204", description = "Successfully deleted inventory record"),
        @ApiResponse(responseCode = "404", description = "Inventory record not found")
    })
    public ResponseEntity<Void> deleteInventory(
            @Parameter(description = "Inventory ID")
            @PathVariable Long id) {
        
        if (inventoryService.deleteInventory(id)) {
            return ResponseEntity.noContent().build();
        } else {
            return ResponseEntity.notFound().build();
        }
    }
}
