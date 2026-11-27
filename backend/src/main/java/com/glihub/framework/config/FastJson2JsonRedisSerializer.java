package com.glihub.framework.config;

import java.nio.charset.StandardCharsets;
import org.springframework.data.redis.serializer.RedisSerializer;
import org.springframework.data.redis.serializer.SerializationException;
import com.alibaba.fastjson2.JSON;

/**
 * Pure UTF-8 JSON serializer for Valkey 9 / Redis (No Java binary serialization, no AutoType).
 */
public class FastJson2JsonRedisSerializer<T> implements RedisSerializer<T>
{
    private final Class<T> clazz;

    public FastJson2JsonRedisSerializer(Class<T> clazz)
    {
        this.clazz = clazz;
    }

    @Override
    public byte[] serialize(T t) throws SerializationException
    {
        if (t == null)
        {
            return new byte[0];
        }
        return JSON.toJSONString(t).getBytes(StandardCharsets.UTF_8);
    }

    @Override
    @SuppressWarnings("unchecked")
    public T deserialize(byte[] bytes) throws SerializationException
    {
        if (bytes == null || bytes.length == 0)
        {
            return null;
        }
        String str = new String(bytes, StandardCharsets.UTF_8);
        if (clazz == Object.class)
        {
            return (T) JSON.parse(str);
        }
        return JSON.parseObject(str, clazz);
    }
}
