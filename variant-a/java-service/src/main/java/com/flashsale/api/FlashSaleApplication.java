package com.flashsale.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.mockito.Mockito;

import javax.sql.DataSource;
import java.io.PrintWriter;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.SQLFeatureNotSupportedException;
import java.util.logging.Logger;

@SpringBootApplication
@EnableCaching
@EnableScheduling
public class FlashSaleApplication {

    public static void main(String[] args) {
        SpringApplication.run(FlashSaleApplication.class, args);
    }

    @Bean
    @Primary
    @ConditionalOnProperty(name = "BENCHMARK_MODE", havingValue = "true")
    public RedisTemplate<String, Object> mockRedisTemplate() {
        return Mockito.mock(RedisTemplate.class);
    }
    
    @Bean
    @Primary
    @ConditionalOnProperty(name = "BENCHMARK_MODE", havingValue = "true")
    public RedisConnectionFactory mockRedisConnectionFactory() {
        return Mockito.mock(RedisConnectionFactory.class);
    }
    
    @Bean
    @Primary
    @ConditionalOnProperty(name = "BENCHMARK_MODE", havingValue = "true")
    public DataSource mockDataSource() {
        return new DataSource() {
            @Override
            public Connection getConnection() throws SQLException { return null; }
            @Override
            public Connection getConnection(String username, String password) throws SQLException { return null; }
            @Override
            public <T> T unwrap(Class<T> iface) throws SQLException { return null; }
            @Override
            public boolean isWrapperFor(Class<?> iface) throws SQLException { return false; }
            @Override
            public PrintWriter getLogWriter() throws SQLException { return null; }
            @Override
            public void setLogWriter(PrintWriter out) throws SQLException {}
            @Override
            public void setLoginTimeout(int seconds) throws SQLException {}
            @Override
            public int getLoginTimeout() throws SQLException { return 0; }
            @Override
            public Logger getParentLogger() throws SQLFeatureNotSupportedException { return null; }
        };
    }
}
