package com.flashsale.api.mapper;

import com.flashsale.api.dto.SpuDtos.*;
import com.flashsale.api.entity.Spu;
import org.mapstruct.*;

@Mapper(componentModel = "spring", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface SpuMapper {

    SpuResponseDto toResponseDto(Spu spu);

    Spu toEntity(SpuCreateDto createDto);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void updateEntityFromDto(SpuUpdateDto updateDto, @MappingTarget Spu spu);
}
