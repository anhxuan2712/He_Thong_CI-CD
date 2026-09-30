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

Sau khi lựa chọn và chuẩn bị nội dung cấu hình CI/CD phù hợp (theo các **Mẫu 1, 2, 3, 4** ở Mục 3), thực hiện kết nối dự án theo các bước chuẩn hóa sau:

---

### Bước 1: Lựa chọn vị trí lưu file cấu hình CI/CD

Tùy theo mô hình quản lý của dự án, bạn chọn 1 trong 2 phương án lưu trữ:

* **Phương án A — Quản lý tập trung tại `gitlab-ci/ci-pipeline` (Khuyến nghị chuẩn FTECH):**
  1. Truy cập repo trung tâm `gitlab-ci/ci-pipeline`.
  2. Tạo thư mục theo tên dự án (ví dụ: `my-project/`).
  3. Thêm file `.gitlab-ci.yml` vào thư mục vừa tạo và dán nội dung cấu hình đã chuẩn bị.
  *(Phương án này giúp code repo của dự án luôn sạch sẽ và DevOps dễ quản lý tập trung).*

* **Phương án B — Quản lý trực tiếp tại Repository dự án:**
  1. Tạo file `.gitlab-ci.yml` ngay tại thư mục gốc (root) của chính repo dự án.
  2. Dán nội dung cấu hình đã chuẩn bị vào file.

---

### Bước 2: Cấu hình tham chiếu CI/CD Configuration File trên GitLab

1. Truy cập vào Repository của dự án trên GitLab ➔ Chọn menu **Settings** ➔ **CI/CD**.
2. Tìm đến mục **General pipelines** và bấm nút **Expand** (Mở rộng).
3. Tại ô **CI/CD configuration file**:
   - **Nếu áp dụng Phương án A (Repo tập trung):** Nhập cú pháp:
     ```text
     <tên_folder>/.gitlab-ci.yml@gitlab-ci/ci-pipeline:main
     ```
     *(Ví dụ: `my-project/.gitlab-ci.yml@gitlab-ci/ci-pipeline:main`)*.
   - **Nếu áp dụng Phương án B (File ở root repo):** Để trống trường này (mặc định GitLab sẽ tự nạp `.gitlab-ci.yml` tại root).
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

### Bước 3: Cấu hình CI/CD Variables cho dự án

Truy cập **Settings** ➔ **CI/CD** ➔ **Variables** ➔ Bấm **Add variable** để khai báo các thông số bắt buộc:

| Tên biến (Key) | Mục đích | Bắt buộc | Ghi chú |
| :--- | :--- | :---: | :--- |
| `SONAR_PROJECT_KEY` | Key định danh dự án trên SonarQube | **Có** | Lấy từ SonarQube Server của FTECH |
| `SONAR_TOKEN` | Token xác thực đẩy kết quả phân tích | **Có** | Masked variable |
| `REGISTRY_PUSH_USER` | Tài khoản đẩy Docker image lên Registry | Tùy chọn | Nếu cần override quyền registry |
| `REGISTRY_PUSH_PASSWORD`| Mật khẩu đẩy Docker image | Tùy chọn | Masked variable |

---

## 5. CHECKLIST KIỂM TRA TRƯỚC KHI GOLIVE CI/CD

- [ ] File `.gitlab-ci.yml` đã include tối thiểu module `devsecops/devsecops-template.yml`.
- [ ] Runner Tags được gắn chính xác: `[devsecops]` cho scan/test, `[build]` cho build Docker.
- [ ] Các thông tin mật (API Keys, Passwords) đã được đưa vào **CI/CD Variables** (không commit cứng vào code).
- [ ] Đã kiểm tra pipeline chạy thành công qua toàn bộ các stage mà không bị block lỗi secret hay SBOM.
