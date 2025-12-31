package com.flashsale.api.repository;

import com.flashsale.api.entity.Spu;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface SpuRepository extends JpaRepository<Spu, UUID> {
    
    Optional<Spu> findBySlug(String slug);
    
    boolean existsBySlug(String slug);
    
    @Query("SELECT s FROM Spu s WHERE s.isActive = :isActive")
    Page<Spu> findByIsActive(@Param("isActive") Boolean isActive, Pageable pageable);
    
    @Query("SELECT s FROM Spu s WHERE s.name LIKE %:name%")
    Page<Spu> findByNameContaining(@Param("name") String name, Pageable pageable);
}
