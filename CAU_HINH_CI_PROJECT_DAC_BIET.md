# KỊCH BẢN CẤU HÌNH CI CHO DỰ ÁN ĐẶC BIỆT 

## 1. TỔNG QUAN & NGUYÊN TẮC THIẾT KẾ

Hệ thống CI/CD tại FTECH được xây dựng theo mô hình **Centralized CI/CD Templates** (Template CI tập trung) lưu trữ tại repository `gitlab-ci/ci-pipeline`.

### Nguyên tắc cốt lõi:
1. **Security-First & Compliance (Tuân thủ an ninh Shift-Left):** Mọi dự án (kể cả dự án đặc biệt) đều bắt buộc phải tuân thủ các bước kiểm tra an toàn thông tin: *Quét lộ lọt bí mật (`detect-secrets`), Phân tích thành phần phần mềm & SBOM (`dependency-check`, `upload-bom`), và Đánh giá chất lượng mã nguồn (`sonarqube-check`)*.
2. **DRY (Don't Repeat Yourself):** Không sao chép toàn bộ mã nguồn của file template về repository dự án. Luôn sử dụng cơ chế `include` từ template tập trung để tự động nhận các bản vá bảo mật và nâng cấp công cụ.
3. **Modular & Selective Override (Kế thừa theo Module & Ghi đè có chọn lọc):** Chỉ ghi đè (override) hoặc mở rộng (extend) những biến, stage hoặc job mà dự án thực sự có sự khác biệt.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      MÔ HÌNH KẾ THỪA & TÙY BIẾN CHUẨN                            │
│                                                                                  │
│   ┌────────────────────────────────┐       ┌─────────────────────────────────┐   │
│   │   gitlab-ci/ci-pipeline        │       │   Project Repository (.gitlab)  │   │
│   │                                │       │                                 │   │
│   │ ├─ devsecops-template.yml ─────┼───────┼──► [BẮT BUỘC INCLUDE]           │   │
│   │ └─ build-template.yml ─────────┼─ - - -┼──► [Tùy chọn Include / Tự viết] │   │
│   └────────────────────────────────┘       │   ├─ Override Variables         │   │
│                                            │   ├─ Bổ sung Custom Jobs (Test) │   │
│                                            │   └─ Định nghĩa Custom Build    │   │
│                                            └─────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PHÂN LOẠI CÁC TRƯỜNG HỢP DỰ ÁN ĐẶC BIỆT

| Nhóm trường hợp | Đặc điểm nhận diện | Giải pháp khuyến nghị |
| :--- | :--- | :--- |
| **Nhóm 1: Tùy biến cấu hình & Đường dẫn** | Thay đổi vị trí `Dockerfile`, thư mục nguồn, tên image. | **Kế thừa đầy đủ + Ghi đè Variables** |
| **Nhóm 2: Bổ sung quy trình kiểm thử** | Cần chạy Unit Test, Linting, Integration Test, Database Migration trước khi build. | **Kế thừa đầy đủ + Thêm Custom Stages/Jobs** |
| **Nhóm 3: Công nghệ Build đặc thù** | Không build Docker tiêu chuẩn (NPM Package, Python Wheel, Mobile App, Helm Chart,...). | **Chỉ kế thừa DevSecOps + Tự định nghĩa Build Job** |
| **Nhóm 4: Đa dịch vụ (Monorepo)** | Một repo chứa nhiều sub-services, chỉ build service có commit thay đổi. | **Sử dụng `rules:changes` + CI Components/Child Pipelines** |

---

## 3. CÁC MẪU CẤU HÌNH CHI TIẾT (GOLDEN TEMPLATES)

---

### MẪU 1: Dự án chuẩn có tùy biến đường dẫn (Nhóm 1)

Áp dụng khi dự án có cấu trúc thư mục khác chuẩn, Dockerfile nằm trong thư mục con.

```yaml
# File: .gitlab-ci.yml
include:
  - project: 'gitlab-ci/ci-pipeline'
    file:
      - 'build-common/build-template.yml'
      - 'devsecops/devsecops-template.yml'

variables:
  PROJECT: "special-api-service"
  CI_REGISTRY: "registry.ftech.ai"
  CI_REGISTRY_IMAGE: "registry.ftech.ai/backend/special-api-service"
  
  # Tùy biến vị trí Dockerfile và Build Context
  DOCKERFILE: "deploy/docker/Dockerfile.production"
  BUILD_FOLDER: "./"

stages:
  - detect-secrets
  - build
  - dependency-check
  - upload-bom
  - sonarqube-check
```

---

### MẪU 2: Dự án cần bổ sung Unit Test / Linting / Code Quality (Nhóm 2 - Khuyến nghị dùng nhiều nhất)

Áp dụng khi dự án cần đảm bảo chất lượng code bằng các bộ test tự động trước khi tiến hành đóng gói Docker image

```yaml
# File: .gitlab-ci.yml
include:
  - project: 'gitlab-ci/ci-pipeline'
    file:
      - 'build-common/build-template.yml'
      - 'devsecops/devsecops-template.yml'

# Khai báo lại stages và chèn thêm stage 'test' hoặc 'lint'
stages:
  - detect-secrets
  - test              # Stage mới của dự án
  - build             # Kế thừa từ build-template.yml
  - dependency-check  # Kế thừa từ devsecops-template.yml
  - upload-bom        # Kế thừa từ devsecops-template.yml
  - sonarqube-check   # Kế thừa từ devsecops-template.yml

variables:
  PROJECT: "user-authentication-service"
  CI_REGISTRY_IMAGE: "registry.ftech.ai/core/user-auth"
  DOCKERFILE: "Dockerfile"
  BUILD_FOLDER: "."

# ==========================================
# CÁC JOB KIỂM THỬ ĐẶC THÙ CỦA DỰ ÁN
# ==========================================
run-linter:
  stage: test
  image: golangci/golangci-lint:v1.54-alpine
  script:
    - golangci-lint run ./...
  tags: [test]
  allow_failure: true

run-unit-tests:
  stage: test
  image: golang:1.21-alpine
  script:
    - go test -v -coverprofile=coverage.txt ./...
  artifacts:
    expire_in: 7 days
    paths:
      - coverage.txt
  tags: [test]
```

---

### MẪU 3: Dự án công nghệ Build đặc thù (Không dùng Docker tiêu chuẩn) (Nhóm 3)

Áp dụng cho các dự án thư viện dùng chung (NPM/PyPI), ứng dụng Native, Serverless hoặc Helm Charts không đóng gói qua `docker:dind`.

```yaml
# File: .gitlab-ci.yml
# CHỈ include devsecops để giữ vững chuẩn an ninh, KHÔNG include build-template
include:
  - project: 'gitlab-ci/ci-pipeline'
    file:
      - 'devsecops/devsecops-template.yml'

stages:
  - detect-secrets
  - build-package     # Stage build riêng của dự án
  - dependency-check  # Vẫn quét thư viện phụ thuộc
  - upload-bom        # Vẫn đẩy SBOM lên Dependency-Track
  - sonarqube-check   # Vẫn kiểm tra chất lượng code

variables:
  PROJECT: "ftech-ui-components"

# ==========================================
# JOB BUILD & PUBLISH PACKAGE RIÊNG BIỆT
# ==========================================
build-and-publish-npm:
  stage: build-package
  image: node:18-alpine
  before_script:
    - echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > .npmrc
  script:
    - npm ci
    - npm run build
    - npm publish --access public
  tags: [build]
  only:
    - tags
    - main
```

---

### MẪU 4: Dự án Monorepo (Nhiều Service trong 1 Repository) (Nhóm 4)

Áp dụng khi một kho chứa có nhiều thư mục con (`services/auth`, `services/payment`,...), chỉ kích hoạt build service nào có thay đổi code.

```yaml
# File: .gitlab-ci.yml
include:
  - project: 'gitlab-ci/ci-pipeline'
    file:
      - 'build-common/build-template.yml'
      - 'devsecops/devsecops-template.yml'

stages:
  - detect-secrets
  - build
  - dependency-check
  - upload-bom
  - sonarqube-check

variables:
  CI_REGISTRY: "registry.ftech.ai"

# ------------------------------------------
# Service Auth
# ------------------------------------------
build-auth-service:
  extends: .build_template
  stage: build
  variables:
    ENV_NAME: dev
    CI_REGISTRY_IMAGE: "registry.ftech.ai/monorepo/auth-service"
    BUILD_FOLDER: "./services/auth"
    DOCKERFILE: "./services/auth/Dockerfile"
  rules:
    - changes:
        - services/auth/**/*

# ------------------------------------------
# Service Payment
# ------------------------------------------
build-payment-service:
  extends: .build_template
  stage: build
  variables:
    ENV_NAME: dev
    CI_REGISTRY_IMAGE: "registry.ftech.ai/monorepo/payment-service"
    BUILD_FOLDER: "./services/payment"
    DOCKERFILE: "./services/payment/Dockerfile"
  rules:
    - changes:
        - services/payment/**/*
```

---


## 4. QUY TRÌNH CẤU HÌNH KẾT NỐI DỰ ÁN TRÊN GITLAB (INTEGRATION WORKFLOW)

Sau khi lựa chọn và chuẩn bị nội dung cấu hình CI/CD phù hợp (theo các **Mẫu 1, 2, 3, 4** ở Mục 3), thực hiện kết nối dự án với hệ thống CI/CD tập trung theo các bước sau:

---

### Bước 1: Lưu file cấu hình vào repository CI/CD tập trung

Theo tiêu chuẩn quản lý CI/CD tập trung tại FTECH, cấu hình pipeline của dự án sẽ được lưu trữ và quản trị tại repo trung tâm `gitlab-ci/ci-pipeline`:

1. Truy cập vào repository `gitlab-ci/ci-pipeline`.
2. Tạo một thư mục mới đặt theo tên của dự án (ví dụ: `my-project/`).
3. Tạo file `.gitlab-ci.yml` bên trong thư mục vừa tạo (đường dẫn dạng: `my-project/.gitlab-ci.yml`).
4. Dán toàn bộ nội dung cấu hình YAML đã chuẩn bị vào file này và thực hiện commit lên nhánh `main`.

*(Cách làm này giúp source code của dự án luôn gọn gàng, đồng thời DevOps có thể chủ động quản trị, cập nhật và kiểm soát tập trung toàn bộ pipeline).*

---

### Bước 2: Cấu hình tham chiếu file CI/CD trên Repository của dự án

Để GitLab Runner tại repository dự án biết và nạp file cấu hình từ repo tập trung:

1. Truy cập vào repository mã nguồn của dự án trên GitLab ➔ Chọn menu **Settings** ➔ **CI/CD**.
2. Tìm đến mục **General pipelines** và bấm nút **Expand** (Mở rộng).
3. Tại ô **CI/CD configuration file**, nhập đường dẫn trỏ về file cấu hình trong repo tập trung theo cú pháp:
   ```text
   <tên_thu_mục>/.gitlab-ci.yml@gitlab-ci/ci-pipeline:main
   ```
   *(Ví dụ: `my-project/.gitlab-ci.yml@gitlab-ci/ci-pipeline:main`)*
4. Bấm **Save changes** (Lưu thay đổi).

```
┌────────────────────────────────────────────────────────────────────────┐
│ GitLab > Project Settings > CI/CD > General pipelines                  │
│                                                                        │
│ CI/CD configuration file                                               │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ my-project/.gitlab-ci.yml@gitlab-ci/ci-pipeline:main               │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ [ Save changes ]                                                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Bước 3: Khai báo CI/CD Variables cho dự án

Các thông tin nhạy cảm (token xác thực, mật khẩu, tài khoản) tuyệt đối không được viết trực tiếp vào mã nguồn hay file `.gitlab-ci.yml`. Thay vào đó, cần khai báo trong mục CI/CD Variables của dự án để pipeline tự động nạp an toàn khi thực thi:

- **Thao tác:** Truy cập **Settings** ➔ **CI/CD** ➔ **Variables** ➔ Bấm **Add variable** để khai báo các biến cần thiết sau:

| Tên biến (Key) | Ý nghĩa & Mục đích sử dụng | Bắt buộc | Cài đặt bảo mật |
| :--- | :--- | :---: | :--- |
| `SONAR_PROJECT_KEY` | **Mã định danh dự án trên SonarQube:** Giúp job `sonarqube-check` định tuyến và gửi kết quả phân tích chất lượng code (Code Smells, Bugs, Security Vulnerabilities) vào đúng Dashboard dự án trên SonarQube Server. | **Có** | Không cần Masked (Lấy Project Key từ SonarQube FTECH) |
| `SONAR_TOKEN` | **Token xác thực SonarQube:** Dùng để chứng thực quyền gửi dữ liệu phân tích từ Runner lên máy chủ SonarQube. | **Có** | Bật **Mask variable** |
| `REGISTRY_PUSH_USER` | **Tài khoản đăng nhập Container Registry:** Sử dụng khi dự án cần phân quyền riêng để đẩy (push) Docker Image lên Harbor/Registry nội bộ. | **Có** | Không cần Masked |
| `REGISTRY_PUSH_PASSWORD` | **Mật khẩu/Secret Token Registry:** Dùng kèm với `REGISTRY_PUSH_USER` để xác thực quyền ghi (push) image lên kho lưu trữ Docker. | **Có** | Bật **Mask variable** |

