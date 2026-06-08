# auth — Java → Python 迁移说明

从 Java Spring Boot + Spring Security 迁移至 FastAPI 的 Azure AD 认证模块。

## 对应关系

| Java | Python |
|------|--------|
| `AdProperties` | `auth/settings.py` `ADProperties` |
| `Helper.transformGroupKeys` | `auth/helper.py` `transform_group_keys` |
| `GraphService` | `auth/graph_service.py` `GraphService` |
| `AuthorizedUserDetailsService` | `auth/user_details.py` `AuthorizedUserDetailsService` |
| Spring Security OIDC | `fastapi-azure-auth` `SingleTenantAzureAuthorizationCodeBearer` |
| `@PreAuthorize("hasAuthority('read')")` | `Depends(require_permission("read"))` |
| `@Profile("!noauth")` | `NOAUTH=true` 环境变量 |

## 认证流程

```
用户浏览器
    ↓ 登录（Azure AD，流程不变）
Azure AD（颁发token）
    ↓
fastapi-azure-auth（验证JWT签名/claims）
    ↓
get_user_permissions()
    ├── GraphService.get_user_group_membership()
    │     └── 用户token → GET /me/memberOf → AD Group IDs
    └── GraphService.get_group_id_name_mapping()
          └── SPN token → GET /groups → {id: name}（TTL缓存5分钟）
    ↓
两层映射：groupId → groupName → permissions
    ↓
require_permission() → HTTP 403 or 通过
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（复用Java那边的Azure AD配置，无需重新申请）
cp .env.example .env
# 编辑 .env 填入 Tenant ID、Client ID、Client Secret

# 3. 启动
uvicorn example_app:app --reload

# 4. 访问 Swagger UI（支持Azure AD登录）
# http://localhost:8000/docs

# 本地开发跳过认证
NOAUTH=true uvicorn example_app:app --reload
```

## 运行测试

```bash
pytest tests/ -v
```

## 关键注意事项

1. **`transformGroupKeys`**：配置文件里`&`写成`SummComp`，代码自动还原成`Summ&Comp`
2. **双身份**：`/me/memberOf` 用用户token；`/groups` 用SPN token
3. **`/me/memberOf` 不支持 server-side `$filter`**，prefix过滤在client-side做
4. **group mapping 缓存5分钟**，生产环境可根据需要调整TTL
5. **Azure配置完全复用Java**，不需要重新向IT申请App Registration
