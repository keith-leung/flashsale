package com.flashsale.api.service;

import com.flashsale.api.dto.FlashSaleDtos.*;
import com.flashsale.api.entity.FlashSaleEvent;
import com.flashsale.api.entity.FlashSaleStatus;
import com.flashsale.api.repository.FlashSaleEventRepository;
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
public class FlashSaleService {

    private static final Logger logger = LoggerFactory.getLogger(FlashSaleService.class);

    private final FlashSaleEventRepository flashSaleEventRepository;

    @Autowired
    public FlashSaleService(FlashSaleEventRepository flashSaleEventRepository) {
        this.flashSaleEventRepository = flashSaleEventRepository;
    }

    @Transactional(readOnly = true)
    public Page<FlashSaleEventResponseDto> getAllFlashSales(int page, int size, FlashSaleStatus status) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<FlashSaleEvent> events;

        if (status != null) {
            events = flashSaleEventRepository.findByStatus(status.name().toLowerCase(), pageable);
        } else {
            events = flashSaleEventRepository.findAll(pageable);
        }

        return events.map(this::toResponseDto);
    }

    @Transactional(readOnly = true)
    public Optional<FlashSaleEventResponseDto> getFlashSaleById(Long id) {
        return flashSaleEventRepository.findById(UUID.fromString(id.toString()))
                .map(this::toResponseDto);
    }

    public FlashSaleEventResponseDto createFlashSale(FlashSaleEventCreateDto createDto) {
        FlashSaleEvent event = new FlashSaleEvent();
        event.setName(createDto.getName());
        event.setDescription(createDto.getDescription());
        event.setSkuId(createDto.getSkuId());
        event.setTotalSaleLimit(createDto.getTotalSaleLimit());
        event.setMaxQuantityPerCustomer(createDto.getMaxQuantityPerCustomer());
        event.setStartTime(createDto.getStartTime());
        event.setEndTime(createDto.getEndTime());
        event.setIsActive(createDto.getIsActive());
        event.setStatus(FlashSaleStatus.scheduled);
        event.setSoldQuantity(0);

        FlashSaleEvent savedEvent = flashSaleEventRepository.save(event);
        logger.info("Created flash sale event with ID: {} and name: {}", savedEvent.getId(), savedEvent.getName());

        return toResponseDto(savedEvent);
    }

    public Optional<FlashSaleEventResponseDto> updateFlashSale(Long id, FlashSaleEventUpdateDto updateDto) {
        return flashSaleEventRepository.findById(UUID.fromString(id.toString()))
                .map(existingEvent -> {
                    if (updateDto.getName() != null) {
                        existingEvent.setName(updateDto.getName());
                    }
                    if (updateDto.getDescription() != null) {
                        existingEvent.setDescription(updateDto.getDescription());
                    }
                    if (updateDto.getTotalSaleLimit() != null) {
                        existingEvent.setTotalSaleLimit(updateDto.getTotalSaleLimit());
                    }
                    if (updateDto.getMaxQuantityPerCustomer() != null) {
                        existingEvent.setMaxQuantityPerCustomer(updateDto.getMaxQuantityPerCustomer());
                    }
                    if (updateDto.getStartTime() != null) {
                        existingEvent.setStartTime(updateDto.getStartTime());
                    }
                    if (updateDto.getEndTime() != null) {
                        existingEvent.setEndTime(updateDto.getEndTime());
                    }
                    if (updateDto.getStatus() != null) {
                        existingEvent.setStatus(updateDto.getStatus());
                    }
                    if (updateDto.getIsActive() != null) {
                        existingEvent.setIsActive(updateDto.getIsActive());
                    }

                    FlashSaleEvent updatedEvent = flashSaleEventRepository.save(existingEvent);
                    logger.info("Updated flash sale event with ID: {}", updatedEvent.getId());

                    return toResponseDto(updatedEvent);
                });
    }

    public boolean deleteFlashSale(Long id) {
        UUID uuid = UUID.fromString(id.toString());
        if (flashSaleEventRepository.existsById(uuid)) {
            flashSaleEventRepository.deleteById(uuid);
            logger.info("Deleted flash sale event with ID: {}", id);
            return true;
        }
        return false;
    }

    public PurchaseResponseDto purchaseFromFlashSale(Long id, PurchaseRequestDto purchaseRequest) {
        UUID uuid = UUID.fromString(id.toString());
        FlashSaleEvent event = flashSaleEventRepository.findById(uuid)
                .orElseThrow(() -> new IllegalArgumentException("Flash sale not found"));

        if (!event.isAvailable()) {
            throw new IllegalStateException("Flash sale is not available");
        }

        if (!event.canPurchaseQuantity(purchaseRequest.getQuantity())) {
            throw new IllegalStateException("Requested quantity not available");
        }

        boolean purchased = event.purchaseQuantity(purchaseRequest.getQuantity());
        if (!purchased) {
            throw new IllegalStateException("Failed to process purchase");
        }

        flashSaleEventRepository.save(event);

        PurchaseResponseDto response = new PurchaseResponseDto();
        response.setSuccess(true);
        response.setMessage("Purchase successful");
        response.setQuantityPurchased(purchaseRequest.getQuantity());
        response.setRemainingQuantity(event.getRemainingQuantity());

        return response;
    }

    private FlashSaleEventResponseDto toResponseDto(FlashSaleEvent event) {
        FlashSaleEventResponseDto dto = new FlashSaleEventResponseDto();
        dto.setId(event.getId());
        dto.setName(event.getName());
        dto.setDescription(event.getDescription());
        dto.setSkuId(event.getSkuId());
        dto.setTotalSaleLimit(event.getTotalSaleLimit());
        dto.setSoldQuantity(event.getSoldQuantity());
        dto.setRemainingQuantity(event.getRemainingQuantity());
        dto.setMaxQuantityPerCustomer(event.getMaxQuantityPerCustomer());
        dto.setStartTime(event.getStartTime());
        dto.setEndTime(event.getEndTime());
        dto.setStatus(event.getStatus());
        dto.setIsActive(event.getIsActive());
        dto.setIsAvailable(event.isAvailable());
        dto.setCreatedAt(event.getCreatedAt());
        dto.setUpdatedAt(event.getUpdatedAt());
        return dto;
    }
}
