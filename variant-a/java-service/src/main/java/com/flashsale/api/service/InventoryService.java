package com.flashsale.api.service;

import com.flashsale.api.dto.InventoryDtos.*;
import com.flashsale.api.entity.Inventory;
import com.flashsale.api.repository.InventoryRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@Transactional
public class InventoryService {

    private static final Logger logger = LoggerFactory.getLogger(InventoryService.class);

    private final InventoryRepository inventoryRepository;

    @Autowired
    public InventoryService(InventoryRepository inventoryRepository) {
        this.inventoryRepository = inventoryRepository;
    }

    @Transactional(readOnly = true)
    public Page<InventoryResponseDto> getAllInventory(int page, int size, Long skuId) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Inventory> inventoryPage;

        if (skuId != null) {
            // Find single inventory by skuId
            Optional<Inventory> inventory = inventoryRepository.findBySkuId(UUID.fromString(skuId.toString()));
            if (inventory.isPresent()) {
                return new PageImpl<>(List.of(toResponseDto(inventory.get())), pageable, 1);
            } else {
                return Page.empty(pageable);
            }
        } else {
            inventoryPage = inventoryRepository.findAll(pageable);
            return inventoryPage.map(this::toResponseDto);
        }
    }

    @Transactional(readOnly = true)
    public Optional<InventoryResponseDto> getInventoryById(Long id) {
        return inventoryRepository.findById(UUID.fromString(id.toString()))
                .map(this::toResponseDto);
    }

    @Transactional(readOnly = true)
    public Optional<InventoryResponseDto> getInventoryBySkuId(Long skuId) {
        return inventoryRepository.findBySkuId(UUID.fromString(skuId.toString()))
                .map(this::toResponseDto);
    }

    public InventoryResponseDto createInventory(InventoryCreateDto createDto) {
        // Check if inventory already exists for this SKU
        if (inventoryRepository.existsBySkuId(createDto.getSkuId())) {
            throw new IllegalArgumentException("Inventory already exists for SKU ID: " + createDto.getSkuId());
        }

        Inventory inventory = new Inventory();
        inventory.setSkuId(createDto.getSkuId());
        inventory.setQuantity(createDto.getQuantity());
        inventory.setReservedQuantity(createDto.getReservedQuantity());
        inventory.setAllowNegativeStock(createDto.getAllowNegativeStock());

        Inventory savedInventory = inventoryRepository.save(inventory);
        logger.info("Created inventory record with ID: {} for SKU: {}", savedInventory.getId(), savedInventory.getSkuId());

        return toResponseDto(savedInventory);
    }

    public Optional<InventoryResponseDto> updateInventory(Long id, InventoryUpdateDto updateDto) {
        return inventoryRepository.findById(UUID.fromString(id.toString()))
                .map(existingInventory -> {
                    if (updateDto.getQuantity() != null) {
                        existingInventory.setQuantity(updateDto.getQuantity());
                    }
                    if (updateDto.getReservedQuantity() != null) {
                        existingInventory.setReservedQuantity(updateDto.getReservedQuantity());
                    }
                    if (updateDto.getAllowNegativeStock() != null) {
                        existingInventory.setAllowNegativeStock(updateDto.getAllowNegativeStock());
                    }

                    Inventory updatedInventory = inventoryRepository.save(existingInventory);
                    logger.info("Updated inventory record with ID: {}", updatedInventory.getId());

                    return toResponseDto(updatedInventory);
                });
    }

    public boolean deleteInventory(Long id) {
        UUID uuid = UUID.fromString(id.toString());
        if (inventoryRepository.existsById(uuid)) {
            inventoryRepository.deleteById(uuid);
            logger.info("Deleted inventory record with ID: {}", id);
            return true;
        }
        return false;
    }

    private InventoryResponseDto toResponseDto(Inventory inventory) {
        InventoryResponseDto dto = new InventoryResponseDto();
        dto.setId(inventory.getId());
        dto.setSkuId(inventory.getSkuId());
        dto.setQuantity(inventory.getQuantity());
        dto.setReservedQuantity(inventory.getReservedQuantity());
        dto.setAvailableQuantity(inventory.getAvailableQuantity());
        dto.setAllowNegativeStock(inventory.getAllowNegativeStock());
        dto.setCreatedAt(inventory.getCreatedAt());
        dto.setUpdatedAt(inventory.getUpdatedAt());
        return dto;
    }
}
