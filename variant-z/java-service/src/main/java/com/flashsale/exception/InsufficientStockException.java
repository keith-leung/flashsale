package com.flashsale.exception;

import com.flashsale.service.dto.InsufficientStockResponse;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

/**
 * Exception thrown when insufficient stock is available.
 */
@ResponseStatus(HttpStatus.BAD_REQUEST)
public class InsufficientStockException extends RuntimeException {

    private final InsufficientStockResponse response;

    public InsufficientStockException(InsufficientStockResponse response) {
        super(response.getMessage());
        this.response = response;
    }

    public InsufficientStockResponse getResponse() {
        return response;
    }
}