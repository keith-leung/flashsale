package com.flashsale.api.controller;

import com.flashsale.api.dto.FlashSaleDtos.*;
import com.flashsale.api.service.FlashSaleService;
import com.flashsale.api.entity.FlashSaleStatus;
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
@RequestMapping("/api/v1/flash-sales")
@Tag(name = "Flash Sale Management", description = "Flash sale event management operations")
public class FlashSaleController {

    private final FlashSaleService flashSaleService;

    @Autowired
    public FlashSaleController(FlashSaleService flashSaleService) {
        this.flashSaleService = flashSaleService;
    }

    @GetMapping
    @Operation(summary = "Get all flash sales", description = "Retrieve a paginated list of all flash sale events")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved flash sales")
    })
    public ResponseEntity<Page<FlashSaleCampaignResponseDto>> getAllFlashSales(
            @Parameter(description = "Page number (0-based)")
            @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "Page size")
            @RequestParam(defaultValue = "20") int size,
            @Parameter(description = "Filter by status")
            @RequestParam(required = false) FlashSaleStatus status) {
        
        Page<FlashSaleCampaignResponseDto> flashSales = flashSaleService.getAllFlashSales(page, size, status);
        return ResponseEntity.ok(flashSales);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get flash sale by ID", description = "Retrieve a specific flash sale event by its ID")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved flash sale"),
        @ApiResponse(responseCode = "404", description = "Flash sale not found")
    })
    public ResponseEntity<FlashSaleCampaignResponseDto> getFlashSaleById(
            @Parameter(description = "Flash Sale ID")
            @PathVariable Long id) {
        
        return flashSaleService.getFlashSaleById(id)
                .map(flashSale -> ResponseEntity.ok(flashSale))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Create new flash sale", description = "Create a new flash sale event")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Successfully created flash sale"),
        @ApiResponse(responseCode = "400", description = "Invalid input")
    })
    public ResponseEntity<FlashSaleCampaignResponseDto> createFlashSale(
            @Parameter(description = "Flash sale creation data")
            @Valid @RequestBody FlashSaleCampaignCreateDto createDto) {
        
        try {
            FlashSaleCampaignResponseDto createdFlashSale = flashSaleService.createFlashSale(createDto);
            return ResponseEntity.status(HttpStatus.CREATED).body(createdFlashSale);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update flash sale", description = "Update an existing flash sale event")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully updated flash sale"),
        @ApiResponse(responseCode = "400", description = "Invalid input"),
        @ApiResponse(responseCode = "404", description = "Flash sale not found")
    })
    public ResponseEntity<FlashSaleCampaignResponseDto> updateFlashSale(
            @Parameter(description = "Flash Sale ID")
            @PathVariable Long id,
            @Parameter(description = "Flash sale update data")
            @Valid @RequestBody FlashSaleCampaignUpdateDto updateDto) {
        
        try {
            return flashSaleService.updateFlashSale(id, updateDto)
                    .map(flashSale -> ResponseEntity.ok(flashSale))
                    .orElse(ResponseEntity.notFound().build());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete flash sale", description = "Delete a flash sale event")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "204", description = "Successfully deleted flash sale"),
        @ApiResponse(responseCode = "404", description = "Flash sale not found")
    })
    public ResponseEntity<Void> deleteFlashSale(
            @Parameter(description = "Flash Sale ID")
            @PathVariable Long id) {
        
        if (flashSaleService.deleteFlashSale(id)) {
            return ResponseEntity.noContent().build();
        } else {
            return ResponseEntity.notFound().build();
        }
    }

    @PostMapping("/{id}/purchase")
    @Operation(summary = "Purchase from flash sale", description = "Purchase items from a flash sale event")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully processed purchase"),
        @ApiResponse(responseCode = "400", description = "Invalid purchase request or insufficient stock"),
        @ApiResponse(responseCode = "404", description = "Flash sale not found")
    })
    public ResponseEntity<PurchaseResponseDto> purchaseFromFlashSale(
            @Parameter(description = "Flash Sale ID")
            @PathVariable Long id,
            @Parameter(description = "Purchase request data")
            @Valid @RequestBody PurchaseRequestDto purchaseRequest) {
        
        try {
            PurchaseResponseDto result = flashSaleService.purchaseFromFlashSale(id, purchaseRequest);
            return ResponseEntity.ok(result);
        } catch (IllegalArgumentException | IllegalStateException e) {
            return ResponseEntity.badRequest().build();
        }
    }
}
