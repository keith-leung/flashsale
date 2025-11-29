package com.flashsale.api.service;

import com.flashsale.api.dto.SkuDtos.*;
import com.flashsale.api.entity.Sku;
import com.flashsale.api.repository.SkuRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;
import java.util.UUID;

@Service
@Transactional
public class SkuService {

    private static final Logger logger = LoggerFactory.getLogger(SkuService.class);

    private final SkuRepository skuRepository;

    @Autowired
    public SkuService(SkuRepository skuRepository) {
        this.skuRepository = skuRepository;
    }

    @Transactional(readOnly = true)
    public Page<SkuResponseDto> getAllSkus(int page, int size, Long spuId) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Sku> skus;
        
        if (spuId != null) {
            skus = skuRepository.findBySpuId(UUID.fromString(spuId.toString()), pageable);
        } else {
            skus = skuRepository.findAll(pageable);
        }
        
        return skus.map(this::toResponseDto);
    }

    @Transactional(readOnly = true)
    public Optional<SkuResponseDto> getSkuById(Long id) {
        return skuRepository.findById(UUID.fromString(id.toString()))
                .map(this::toResponseDto);
    }

    public SkuResponseDto createSku(SkuCreateDto createDto) {
        // Check if SKU code already exists
        if (skuRepository.existsBySkuCode(createDto.getSkuCode())) {
            throw new IllegalArgumentException("SKU with code '" + createDto.getSkuCode() + "' already exists");
        }

        Sku sku = new Sku();
        sku.setSkuCode(createDto.getSkuCode());
        sku.setName(createDto.getName());
        sku.setSpuId(createDto.getSpuId());
        sku.setPrice(createDto.getPrice());
        sku.setCostPrice(createDto.getCostPrice());
        sku.setWeight(createDto.getWeight());
        sku.setTrackInventory(createDto.getTrackInventory());
        sku.setIsActive(createDto.getIsActive());

        Sku savedSku = skuRepository.save(sku);
        logger.info("Created SKU with ID: {} and code: {}", savedSku.getId(), savedSku.getSkuCode());

        return toResponseDto(savedSku);
    }

    public Optional<SkuResponseDto> updateSku(Long id, SkuUpdateDto updateDto) {
        return skuRepository.findById(UUID.fromString(id.toString()))
                .map(existingSku -> {
                    if (updateDto.getSkuCode() != null) {
                        // Check uniqueness if code is being changed
                        if (!updateDto.getSkuCode().equals(existingSku.getSkuCode()) &&
                            skuRepository.existsBySkuCode(updateDto.getSkuCode())) {
                            throw new IllegalArgumentException("SKU with code '" + updateDto.getSkuCode() + "' already exists");
                        }
                        existingSku.setSkuCode(updateDto.getSkuCode());
                    }
                    if (updateDto.getName() != null) {
                        existingSku.setName(updateDto.getName());
                    }
                    if (updateDto.getPrice() != null) {
                        existingSku.setPrice(updateDto.getPrice());
                    }
                    if (updateDto.getCostPrice() != null) {
                        existingSku.setCostPrice(updateDto.getCostPrice());
                    }
                    if (updateDto.getWeight() != null) {
                        existingSku.setWeight(updateDto.getWeight());
                    }
                    if (updateDto.getTrackInventory() != null) {
                        existingSku.setTrackInventory(updateDto.getTrackInventory());
                    }
                    if (updateDto.getIsActive() != null) {
                        existingSku.setIsActive(updateDto.getIsActive());
                    }

                    Sku updatedSku = skuRepository.save(existingSku);
                    logger.info("Updated SKU with ID: {}", updatedSku.getId());

                    return toResponseDto(updatedSku);
                });
    }

    public boolean deleteSku(Long id) {
        UUID uuid = UUID.fromString(id.toString());
        if (skuRepository.existsById(uuid)) {
            skuRepository.deleteById(uuid);
            logger.info("Deleted SKU with ID: {}", id);
            return true;
        }
        return false;
    }

    private SkuResponseDto toResponseDto(Sku sku) {
        SkuResponseDto dto = new SkuResponseDto();
        dto.setId(sku.getId());
        dto.setSkuCode(sku.getSkuCode());
        dto.setName(sku.getName());
        dto.setSpuId(sku.getSpuId());
        dto.setPrice(sku.getPrice());
        dto.setCostPrice(sku.getCostPrice());
        dto.setWeight(sku.getWeight());
        dto.setTrackInventory(sku.getTrackInventory());
        dto.setIsActive(sku.getIsActive());
        dto.setCreatedAt(sku.getCreatedAt());
        dto.setUpdatedAt(sku.getUpdatedAt());
        return dto;
    }
}
