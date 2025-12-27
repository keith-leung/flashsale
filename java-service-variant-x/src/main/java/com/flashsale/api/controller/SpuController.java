package com.flashsale.api.controller;

import com.flashsale.api.dto.SpuDtos.*;
import com.flashsale.api.service.SpuService;
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

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/spus")
@Tag(name = "SPU Management", description = "Standard Product Unit management operations")
public class SpuController {

    private final SpuService spuService;

    @Autowired
    public SpuController(SpuService spuService) {
        this.spuService = spuService;
    }

    @GetMapping
    @Operation(summary = "Get all SPUs", description = "Retrieve a paginated list of all Standard Product Units")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved SPUs")
    })
    public ResponseEntity<Page<SpuResponseDto>> getAllSpus(
            @Parameter(description = "Page number (0-based)")
            @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "Page size")
            @RequestParam(defaultValue = "20") int size) {
        
        Page<SpuResponseDto> spus = spuService.getAllSpus(page, size);
        return ResponseEntity.ok(spus);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get SPU by ID", description = "Retrieve a specific Standard Product Unit by its ID")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully retrieved SPU"),
        @ApiResponse(responseCode = "404", description = "SPU not found")
    })
    public ResponseEntity<SpuResponseDto> getSpuById(
            @Parameter(description = "SPU ID")
            @PathVariable UUID id) {
        
        return spuService.getSpuById(id)
                .map(spu -> ResponseEntity.ok(spu))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Create new SPU", description = "Create a new Standard Product Unit")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Successfully created SPU"),
        @ApiResponse(responseCode = "400", description = "Invalid input or slug already exists")
    })
    public ResponseEntity<SpuResponseDto> createSpu(
            @Parameter(description = "SPU creation data")
            @Valid @RequestBody SpuCreateDto createDto) {
        
        try {
            SpuResponseDto createdSpu = spuService.createSpu(createDto);
            return ResponseEntity.status(HttpStatus.CREATED).body(createdSpu);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update SPU", description = "Update an existing Standard Product Unit")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Successfully updated SPU"),
        @ApiResponse(responseCode = "400", description = "Invalid input or slug already exists"),
        @ApiResponse(responseCode = "404", description = "SPU not found")
    })
    public ResponseEntity<SpuResponseDto> updateSpu(
            @Parameter(description = "SPU ID")
            @PathVariable UUID id,
            @Parameter(description = "SPU update data")
            @Valid @RequestBody SpuUpdateDto updateDto) {
        
        try {
            return spuService.updateSpu(id, updateDto)
                    .map(spu -> ResponseEntity.ok(spu))
                    .orElse(ResponseEntity.notFound().build());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete SPU", description = "Delete a Standard Product Unit")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "204", description = "Successfully deleted SPU"),
        @ApiResponse(responseCode = "404", description = "SPU not found")
    })
    public ResponseEntity<Void> deleteSpu(
            @Parameter(description = "SPU ID")
            @PathVariable UUID id) {
        
        if (spuService.deleteSpu(id)) {
            return ResponseEntity.noContent().build();
        } else {
            return ResponseEntity.notFound().build();
        }
    }
}
