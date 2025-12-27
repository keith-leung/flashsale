package com.flashsale.api.service;

import com.flashsale.api.dto.SpuDtos.SpuCreateDto;
import com.flashsale.api.dto.SpuDtos.SpuResponseDto;
import com.flashsale.api.dto.SpuDtos.SpuUpdateDto;
import com.flashsale.api.entity.Spu;
import com.flashsale.api.mapper.SpuMapper;
import com.flashsale.api.repository.SpuRepository;
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
public class SpuService {

    private static final Logger logger = LoggerFactory.getLogger(SpuService.class);

    private final SpuRepository spuRepository;
    private final SpuMapper spuMapper;

    @Autowired
    public SpuService(SpuRepository spuRepository, SpuMapper spuMapper) {
        this.spuRepository = spuRepository;
        this.spuMapper = spuMapper;
    }

    @Transactional(readOnly = true)
    public Page<SpuResponseDto> getAllSpus(int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Spu> spus = spuRepository.findAll(pageable);
        return spus.map(spuMapper::toResponseDto);
    }

    @Transactional(readOnly = true)
    public Optional<SpuResponseDto> getSpuById(UUID id) {
        return spuRepository.findById(id)
                .map(spuMapper::toResponseDto);
    }

    @Transactional(readOnly = true)
    public Optional<SpuResponseDto> getSpuBySlug(String slug) {
        return spuRepository.findBySlug(slug)
                .map(spuMapper::toResponseDto);
    }

    public SpuResponseDto createSpu(SpuCreateDto createDto) {
        // Check if slug already exists
        if (spuRepository.existsBySlug(createDto.getSlug())) {
            throw new IllegalArgumentException("SPU with slug '" + createDto.getSlug() + "' already exists");
        }

        Spu spu = spuMapper.toEntity(createDto);
        Spu savedSpu = spuRepository.save(spu);

        logger.info("Created SPU with ID: {} and name: {}", savedSpu.getId(), savedSpu.getName());

        return spuMapper.toResponseDto(savedSpu);
    }

    public Optional<SpuResponseDto> updateSpu(UUID id, SpuUpdateDto updateDto) {
        return spuRepository.findById(id)
                .map(existingSpu -> {
                    // Check slug uniqueness if being updated
                    if (updateDto.getSlug() != null && 
                        !updateDto.getSlug().equals(existingSpu.getSlug()) &&
                        spuRepository.existsBySlug(updateDto.getSlug())) {
                        throw new IllegalArgumentException("SPU with slug '" + updateDto.getSlug() + "' already exists");
                    }

                    spuMapper.updateEntityFromDto(updateDto, existingSpu);
                    Spu updatedSpu = spuRepository.save(existingSpu);

                    logger.info("Updated SPU with ID: {}", updatedSpu.getId());

                    return spuMapper.toResponseDto(updatedSpu);
                });
    }

    public boolean deleteSpu(UUID id) {
        if (spuRepository.existsById(id)) {
            spuRepository.deleteById(id);
            logger.info("Deleted SPU with ID: {}", id);
            return true;
        }
        return false;
    }
}
