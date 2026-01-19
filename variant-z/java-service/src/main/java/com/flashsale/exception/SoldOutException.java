package com.flashsale.exception;

import com.flashsale.service.dto.FlashSaleSoldOutResponse;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

/**
 * Exception thrown when flash sale campaign is sold out.
 */
@ResponseStatus(HttpStatus.BAD_REQUEST)
public class SoldOutException extends RuntimeException {

    private final FlashSaleSoldOutResponse response;

    public SoldOutException(FlashSaleSoldOutResponse response) {
        super(response.getMessage());
        this.response = response;
    }

    public FlashSaleSoldOutResponse getResponse() {
        return response;
    }
}