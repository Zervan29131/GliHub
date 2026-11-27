package com.glihub.common.config.serializer;

import java.util.Objects;
import tools.jackson.core.JacksonException;
import tools.jackson.core.JsonGenerator;
import tools.jackson.databind.BeanProperty;
import tools.jackson.databind.SerializationContext;
import tools.jackson.databind.ValueSerializer;
import com.glihub.common.annotation.Sensitive;
import com.glihub.common.core.domain.model.LoginUser;
import com.glihub.common.enums.DesensitizedType;
import com.glihub.common.utils.SecurityUtils;

public class SensitiveJsonSerializer extends ValueSerializer<String>
{
    private DesensitizedType desensitizedType;

    @Override
    public void serialize(String value, JsonGenerator gen, SerializationContext ctxt) throws JacksonException
    {
        if (desensitization() && desensitizedType != null)
        {
            gen.writeString(desensitizedType.desensitizer().apply(value));
        }
        else
        {
            gen.writeString(value);
        }
    }

    @Override
    public ValueSerializer<?> createContextual(SerializationContext ctxt, BeanProperty property)
    {
        if (property != null)
        {
            Sensitive annotation = property.getAnnotation(Sensitive.class);
            if (Objects.nonNull(annotation) && Objects.equals(String.class, property.getType().getRawClass()))
            {
                SensitiveJsonSerializer custom = new SensitiveJsonSerializer();
                custom.desensitizedType = annotation.desensitizedType();
                return custom;
            }
            return ctxt.findValueSerializer(property.getType());
        }
        return this;
    }

    private boolean desensitization()
    {
        try
        {
            LoginUser securityUser = SecurityUtils.getLoginUser();
            return !securityUser.getUser().isAdmin();
        }
        catch (Exception e)
        {
            return true;
        }
    }
}
