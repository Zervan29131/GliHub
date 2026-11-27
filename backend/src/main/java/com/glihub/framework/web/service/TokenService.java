package com.glihub.framework.web.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import javax.crypto.SecretKey;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import com.glihub.common.constant.CacheConstants;
import com.glihub.common.constant.Constants;
import com.glihub.common.core.domain.model.LoginUser;
import com.glihub.common.core.redis.RedisCache;
import com.glihub.common.utils.ServletUtils;
import com.glihub.common.utils.StringUtils;
import com.glihub.common.utils.ip.AddressUtils;
import com.glihub.common.utils.ip.IpUtils;
import com.glihub.common.utils.uuid.IdUtils;
import eu.bitwalker.useragentutils.UserAgent;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

@Component
public class TokenService
{
    private static final Logger log = LoggerFactory.getLogger(TokenService.class);

    @Value("${token.header}")
    private String header;

    @Value("${token.secret}")
    private String secret;

    @Value("${token.expireTime}")
    private int expireTime;

    protected static final long MILLIS_SECOND = 1000;
    protected static final long MILLIS_MINUTE = 60 * MILLIS_SECOND;
    private static final Long MILLIS_MINUTE_TEN = 20 * 60 * 1000L;

    @Autowired
    private RedisCache redisCache;

    private SecretKey signingKey()
    {
        try
        {
            byte[] digest = MessageDigest.getInstance("SHA-512")
                    .digest((secret != null ? secret : "glihub-v3").getBytes(StandardCharsets.UTF_8));
            return Keys.hmacShaKeyFor(digest);
        }
        catch (Exception ex)
        {
            throw new IllegalStateException("Unable to derive JWT HMAC key", ex);
        }
    }

    public LoginUser getLoginUser(HttpServletRequest request)
    {
        String token = getToken(request);
        if (StringUtils.isNotEmpty(token))
        {
            try
            {
                Claims claims = parseToken(token);
                String uuid = (String) claims.get(Constants.LOGIN_USER_KEY);
                String userKey = getTokenKey(uuid);
                return redisCache.getCacheObject(userKey, LoginUser.class);
            }
            catch (Exception e)
            {
                log.error("获取用户信息异常'{}'", e.getMessage());
            }
        }
        return null;
    }

    public void setLoginUser(LoginUser loginUser)
    {
        if (StringUtils.isNotNull(loginUser) && StringUtils.isNotEmpty(loginUser.getToken()))
        {
            refreshToken(loginUser);
        }
    }

    public void delLoginUser(String token)
    {
        if (StringUtils.isNotEmpty(token))
        {
            redisCache.deleteObject(getTokenKey(token));
        }
    }

    public String createToken(LoginUser loginUser)
    {
        String token = IdUtils.fastUUID();
        loginUser.setToken(token);
        setUserAgent(loginUser);
        refreshToken(loginUser);

        Map<String, Object> claims = new HashMap<>();
        claims.put(Constants.LOGIN_USER_KEY, token);
        return createToken(claims);
    }

    public void verifyToken(LoginUser loginUser)
    {
        if (loginUser.getExpireTime() - System.currentTimeMillis() <= MILLIS_MINUTE_TEN)
        {
            refreshToken(loginUser);
        }
    }

    public void refreshToken(LoginUser loginUser)
    {
        loginUser.setLoginTime(System.currentTimeMillis());
        loginUser.setExpireTime(loginUser.getLoginTime() + expireTime * MILLIS_MINUTE);
        String userKey = getTokenKey(loginUser.getToken());
        redisCache.setCacheObject(userKey, loginUser, expireTime, TimeUnit.MINUTES);
    }

    public void setUserAgent(LoginUser loginUser)
    {
        HttpServletRequest req = ServletUtils.getRequest();
        if (req != null)
        {
            UserAgent userAgent = UserAgent.parseUserAgentString(req.getHeader("User-Agent"));
            String ip = IpUtils.getIpAddr();
            loginUser.setIpaddr(ip);
            loginUser.setLoginLocation(AddressUtils.getRealAddressByIP(ip));
            loginUser.setBrowser(userAgent.getBrowser().getName());
            loginUser.setOs(userAgent.getOperatingSystem().getName());
        }
    }

    private static final io.jsonwebtoken.io.Serializer<Map<String, ?>> JWT_SERIALIZER = new io.jsonwebtoken.io.Serializer<>()
    {
        @Override
        public byte[] serialize(Map<String, ?> map)
        {
            return com.alibaba.fastjson2.JSON.toJSONString(map).getBytes(StandardCharsets.UTF_8);
        }

        @Override
        public void serialize(Map<String, ?> map, java.io.OutputStream out)
        {
            try
            {
                out.write(serialize(map));
            }
            catch (java.io.IOException e)
            {
                throw new io.jsonwebtoken.io.SerializationException("JWT serialize error", e);
            }
        }
    };

    private static final io.jsonwebtoken.io.Deserializer<Map<String, ?>> JWT_DESERIALIZER = new io.jsonwebtoken.io.Deserializer<>()
    {
        @Override
        @SuppressWarnings("unchecked")
        public Map<String, ?> deserialize(byte[] bytes)
        {
            return com.alibaba.fastjson2.JSON.parseObject(new String(bytes, StandardCharsets.UTF_8), Map.class);
        }

        @Override
        @SuppressWarnings("unchecked")
        public Map<String, ?> deserialize(java.io.Reader reader)
        {
            try
            {
                StringBuilder sb = new StringBuilder();
                char[] buf = new char[512];
                int n;
                while ((n = reader.read(buf)) != -1) sb.append(buf, 0, n);
                return com.alibaba.fastjson2.JSON.parseObject(sb.toString(), Map.class);
            }
            catch (java.io.IOException e)
            {
                throw new io.jsonwebtoken.io.DeserializationException("JWT deserialize error", e);
            }
        }
    };

    private String createToken(Map<String, Object> claims)
    {
        return Jwts.builder()
                .json(JWT_SERIALIZER)
                .claims(claims)
                .signWith(signingKey(), Jwts.SIG.HS512)
                .compact();
    }

    private Claims parseToken(String token)
    {
        return Jwts.parser()
                .json(JWT_DESERIALIZER)
                .verifyWith(signingKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    public String getUsernameFromToken(String token)
    {
        return parseToken(token).getSubject();
    }

    private String getToken(HttpServletRequest request)
    {
        String token = request.getHeader(header);
        if (StringUtils.isNotEmpty(token) && token.startsWith(Constants.TOKEN_PREFIX))
        {
            token = token.replace(Constants.TOKEN_PREFIX, "");
        }
        return token;
    }

    private String getTokenKey(String uuid)
    {
        return CacheConstants.LOGIN_TOKEN_KEY + uuid;
    }
}
