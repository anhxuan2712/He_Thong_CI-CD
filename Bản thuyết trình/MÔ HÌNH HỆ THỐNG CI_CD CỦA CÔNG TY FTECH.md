# BÁO CÁO: LUỒNG THỰC THI CI/CD TỪ DEVELOPER PUSH CODE ĐẾN HOÀN TẤT STAGE BUILD VÀ DETECT-SECRETS

```yaml
# File cấu hình .gitlab-ci.yml tại repository của dự án
include:
  - project: 'gitlab-ci/ci-pipeline'
    file:
      - 'build-common/build-template.yml'
      - 'devsecops/devsecops-template.yml'

variables:
  PROJECT: "project-name"
  CI_REGISTRY: "registry.ftech.ai"
  CI_REGISTRY_IMAGE: "registry.ftech.ai/ftech/project-name"
  DOCKER_VERSION: "20.10.16"
  DOCKER_DIND_VERSION: "20.10.16-dind"

stages:
  - build
  - detect-secrets
  - dependency-check
  - upload-bom
  - sonarqube-check
  # gitlabci-analyser: tuỳ chọn, project tự thêm nếu muốn dùng, không có sẵn trong README mẫu
```

## 1. TỔNG QUAN LUỒNG THỰC THI (WORKFLOW OVERVIEW)

Hệ thống CI/CD của FTECH được xây dựng trên nền tảng **GitLab CI/CD**, sử dụng mô hình **Centralized CI Templates** lưu tại repository `gitlab-ci/ci-pipeline`. Quy trình xử lý từ khi Developer đẩy mã nguồn đến khi hoàn tất 2 stage kiểm soát chất lượng và đóng gói ban đầu (`build` và `detect-secrets`) được mô tả tổng quan qua sơ đồ sau:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        1. GIAI ĐOẠN KHỞI TẠO PIPELINE (GITLAB SERVER)                                   │
│                                                                                                         │
│  [Developer] ──── git push ────► [GitLab Server] ────► [Merge Template gitlab-ci/ci-pipeline]           │
│                                                              │                                          │
│                                                              ▼                                          │
│                                          [Xác định thứ tự Stage: build ──► detect-secrets]              │
└──────────────────────────────────────────────────────────────┬──────────────────────────────────────────┘
                                                               │
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        2. STAGE: build (Chạy trước - Tag: build)                                        │
│                                                                                                         │
│  Kiểm tra nhánh (only:) ──┬── dev / develop ────────► Job: build-dev     (Tự động)                      │
│                           ├── staging ──────────────► Job: build-staging (Tự động)                      │
│                           └── main/master/prod/tags ─► Job: build-prod    (when: manual ➔ Bấm Play)    │
│                                                             │                                           │
│                                                             ▼ (Runner tag: build nhận job)              │
│                           ┌─────────────────────────────────────────────────────────────────┐           │
│                           │ Khởi tạo 2 Container (Docker-in-Docker - DinD):                 │           │
│                           │ ├─ docker:20.10.16      (Container chính: Chạy Docker CLI)      │           │
│                           │ └─ docker:20.10.16-dind (Service Daemon: Build/Push Engine)     │           │
│                           │ ─────────────────────────────────────────────────────────────── │           │
│                           │ • before_script: docker login vào registry.ftech.ai             │           │
│                           │ • script: docker build & push "$CI_REGISTRY_IMAGE:$APP_VERSION" │           │
│                           └─────────────────────────────────┬───────────────────────────────┘           │
│                                                             │                                           │
│  [allow_failure: false]                                     ▼                                           │
│    ├─❌ BUILD THẤT BẠI ─────────────────────────► [DỪNG PIPELINE ➔ Báo lỗi Developer]                  │
│    └─✅ BUILD THÀNH CÔNG (PASS)                                                                         │
└─────────────────────────────────────────────────────────────┬───────────────────────────────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        3. STAGE: detect-secrets (Chạy sau - Tag: devsecops)                             │
│                                                                                                         │
│  GitLab Runner tag: devsecops nhận job                                                                  │
│  │                                                                                                      │
│  ▼                                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐           │
│  │ Khởi tạo 1 Container duy nhất (Single Container - Không cần DinD):                       │           │
│  │ Image: registry.ftech.ai/public/is-chart/detect-secrets:v2.8                             │           │
│  │ ──────────────────────────────────────────────────────────────────────────────────────── │           │
│  │ • rm -rf .git/                   (Xoá lịch sử Git, chỉ quét mã nguồn commit hiện tại)    │           │
│  │ • python /app/detect-secrets.py  (Quét secret/token/key; lọc theo EXCLUDE_SECRETS/FOLDERS)│          │
│  └──────────────────────────────────────────┬───────────────────────────────────────────────┘           │
│                                             │                                                           │
│  [allow_failure: false]                     ▼                                                           │
│    ├─❌ PHÁT HIỆN SECRET CHƯA WHITELIST ────► [DỪNG PIPELINE ➔ Báo lỗi Developer]                      │
│    └─✅ MÃ NGUỒN SẠCH (PASS) ───────────────► [Chuyển tiếp sang Stage 3: dependency-check]              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PHẦN CHUNG: GIAI ĐOẠN KHỞI TẠO PIPELINE (GITLAB SERVER)

*Giai đoạn này diễn ra tập trung tại GitLab Server trước khi điều phối công việc xuống các máy chủ thực thi (GitLab Runners).*

### 1. Sự kiện kích hoạt Pipeline (Pipeline Trigger)
- **Hành động:** Developer thực hiện lệnh `git push` mã nguồn từ máy local lên bất kỳ nhánh (`branch`) hoặc gắn nhãn (`tag`) nào trên GitLab Server.
- **Phản ứng của GitLab:** GitLab Server bắt được sự kiện Git Push Event và tự động khởi tạo (trigger) một Pipeline CI/CD mới cho commit tương ứng mà không yêu cầu thao tác bấm nút thủ công.

### 2. Đọc và hợp nhất cấu hình (Config Parsing & Include Merging)
- **Đọc file cấu hình gốc:** GitLab CI Parser đọc file `.gitlab-ci.yml` tại thư mục gốc của repository dự án.
- **Kéo template tập trung (`include`):** Khi gặp chỉ thị `include`, GitLab sẽ phân giải và tải các file template từ repository trung tâm `gitlab-ci/ci-pipeline`:
  - `build-common/build-template.yml` (hoặc `build/build-template.yml`)
  - `devsecops/devsecops-template.yml`
- **Hợp nhất (Merge Engine):** 
  - GitLab thực hiện hợp nhất toàn bộ khai báo biến (`variables`), cấu hình job ẩn định nghĩa khuôn mẫu (`.build_template: &build`), các merge key (`<<: *build`), và các job cụ thể vào một cây cấu hình pipeline thống nhất.
  - Các biến toàn cục (`BUILD_FOLDER`, `DOCKERFILE`, `CI_REGISTRY`, `DOCKER_VERSION`, `RESULT`...) được nạp sẵn vào cấu hình thực thi.

### 3. Xác định thứ tự Stage (Stage Execution Graph)
- Dựa trên khai báo `stages:` trong `.gitlab-ci.yml`:
  ```yaml
  stages:
    - build
    - detect-secrets
    - dependency-check
    - upload-bom
    - sonarqube-check
    # gitlabci-analyser: tuỳ chọn, project tự thêm nếu muốn dùng, không có sẵn trong README mẫu
  ```
- **Quy tắc thực thi tuần tự:** Stage `build` đứng vị trí đầu tiên, tiếp theo là stage `detect-secrets`.
- **Ràng buộc:** Tất cả các job thuộc stage `build` được kích hoạt phải kết thúc thành công (`passed`) thì stage `detect-secrets` mới được GitLab Server lên lịch (`schedule`) để chạy.

---

## 3. PHẦN A: STAGE `build` (ĐÓNG GÓI VÀ ĐẨY DOCKER IMAGE)

*Stage này chịu trách nhiệm đóng gói mã nguồn ứng dụng thành Docker Image và đẩy lên FTECH Private Container Registry (`registry.ftech.ai`).*

### A4. Xác định Job được kích hoạt (Rule Matching)
- GitLab kiểm tra nhánh/tag vừa push đối chiếu với điều kiện `only:` của 3 job build được khai báo trong template:
  - `build-dev`: Kích hoạt khi push vào nhánh `dev`, `develop` (chạy tự động).
  - `build-staging`: Kích hoạt khi push vào nhánh `staging` (chạy tự động).
  - `build-prod`: Kích hoạt khi push vào nhánh `main`, `master`, `prod`, hoặc `tags`. Job này có cấu hình `when: manual` nên sau khi stage khởi tạo, job sẽ dừng ở trạng thái chờ và **cần người quản trị/lead bấm nút "Play" (Run)** trên giao diện GitLab để thực thi.
- **Đặc điểm:** Tại một thời điểm push lên một nhánh xác định, **chỉ duy nhất đúng 1 job build** thỏa mãn điều kiện và được chuyển sang trạng thái `pending`.

### A5. Runner nhận Job (Job Dispatching)
- Các máy chủ **GitLab Runner** được gắn tag `[build]` liên tục gửi yêu cầu kiểm tra (long-polling) đến GitLab Server.
- Khi phát hiện job ở trạng thái `pending` khớp đúng tag `build`, Runner sẽ tiếp nhận job, tải toàn bộ metadata cấu hình (tên image, services, script, biến môi trường...) về để xử lý.

### A6. Chuẩn bị Executor (Docker-in-Docker Executor)
- Vì job khai báo đồng thời `image: docker:$DOCKER_VERSION` và `services: - name: docker:$DOCKER_DIND_VERSION`, Runner bắt buộc phải sử dụng **Docker Executor** với quyền `privileged: true` trên cấu hình Runner.
- Docker Executor hỗ trợ thiết lập mô hình multi-container trên cùng một mạng bridge ảo nội bộ của job.

### A7. Tải Image (Pulling Container Images)
Runner thực hiện kéo 2 image chính thức từ **Docker Hub** (khác với image ứng dụng và các image nội bộ như `is-chart/detect-secrets`, vốn lưu trên **Harbor** tại `registry.ftech.ai`):
1. **Container chính (App/CLI Container):** `docker:20.10.16` — Chỉ chứa Docker CLI, dùng để chạy các dòng lệnh trong `before_script` và `script`.
2. **Container dịch vụ (Service/Daemon Container):** `docker:20.10.16-dind` — Chứa Docker Daemon thật (`dockerd`), chịu trách nhiệm biên dịch và quản lý các layer Docker image.

### A8. Khởi tạo Container và Mạng nội bộ (Container & Network Creation)
- Runner tạo một mạng bridge riêng biệt cho job.
- Khởi động service container với `alias: docker`. Container này lắng nghe các lệnh Docker engine từ mạng nội bộ.
- Khởi động container chính và trỏ biến kết nối Docker Client đến daemon thông qua alias `docker` (`tcp://docker:2375` hoặc `tcp://docker:2376` khi dùng TLS).

### A9. Clone / Checkout mã nguồn (Fetch Workspace)
- Container phụ (`gitlab-runner-helper`) thực hiện clone mã nguồn dự án từ GitLab Server về thư mục làm việc (workspace volume) chung của job, checkout chính xác tại commit SHA vừa push. Mã nguồn này sẵn sàng cho lệnh `docker build`.

### A10. Tiêm nạp biến môi trường (Environment Injection)
Runner tiêm đầy đủ các tầng biến môi trường vào container chính:
- **Biến mặc định của GitLab:** `CI_COMMIT_TAG`, `CI_COMMIT_SHORT_SHA`, `CI_REGISTRY_IMAGE`, `CI_PROJECT_DIR`...
- **Biến toàn cục (Global Variables):** `BUILD_FOLDER: "."`, `DOCKERFILE: "Dockerfile"`, `CI_REGISTRY: "registry.ftech.ai"`, `DOCKER_VERSION: "20.10.16"`, `DOCKER_DIND_VERSION: "20.10.16-dind"`.
- **Biến riêng theo từng Job:** `ENV_NAME` (nhận giá trị `dev`, `staging`, hoặc `prod`).
- **Biến bảo mật (CI/CD Settings Variables):** `REGISTRY_PUSH_USER`, `REGISTRY_PUSH_PASSWORD` (thông tin tài khoản đẩy image lên registry).

### A11. Thực thi tập lệnh (Script Execution)
Tiến trình thực thi theo 2 giai đoạn:

```sh
# 1. Giai đoạn before_script (Kiểm tra & Đăng nhập)
docker info                                              # Kiểm tra tình trạng hoạt động của Docker daemon
docker images                                            # Liệt kê các image cục bộ hiện tại
echo $REGISTRY_PUSH_USER                                 # In thông tin user (khuyến nghị Masked trên GitLab)
echo $REGISTRY_PUSH_PASSWORD                             # In thông tin password (khuyến nghị Masked trên GitLab)
echo $CI_REGISTRY                                        # In registry URL (registry.ftech.ai)
docker login -u "$REGISTRY_PUSH_USER" -p "$REGISTRY_PUSH_PASSWORD" "$CI_REGISTRY" # Đăng nhập Private Registry

# 2. Giai đoạn script (Gắn tag, Build và Push Image)
# Tính toán APP_VERSION: kết hợp ENV_NAME + Timestamp + (Tag hoặc Commit Short SHA)
export APP_VERSION=$ENV_NAME-$(date +'%Y-%m-%d_%H-%M-%S')-`[ -n "$CI_COMMIT_TAG" ] && echo $CI_COMMIT_TAG || echo $CI_COMMIT_SHORT_SHA` && echo $APP_VERSION

# Đóng gói image với 2 tag (tag có phiên bản cụ thể và tag base)
docker build -t "$CI_REGISTRY_IMAGE:$APP_VERSION" -t "$CI_REGISTRY_IMAGE" $BUILD_FOLDER -f $DOCKERFILE

# Đẩy image kèm version lên Private Registry
docker push "$CI_REGISTRY_IMAGE:$APP_VERSION"
```

> [!WARNING]
> **Lưu ý an toàn:** Các lệnh `echo $REGISTRY_PUSH_USER` và `echo $REGISTRY_PUSH_PASSWORD` trong `before_script` in trực tiếp thông tin xác thực ra console log. Cần đảm bảo các biến này được bật tùy chọn **Masked** trong phần *Settings > CI/CD > Variables* của GitLab để tránh rò rỉ thông tin nhạy cảm.

### A12. Thu thập Log và Exit Code
- Mọi luồng xuất chuẩn (`stdout`) và lỗi chuẩn (`stderr`) được gửi theo thời gian thực về máy chủ GitLab để hiển thị trên web console.
- Nếu tất cả các lệnh thực thi trả về `exit code = 0`, job được đánh dấu là `passed`.
- Nếu có bất kỳ lệnh nào thất bại (sai tài khoản đăng nhập registry, lỗi cú pháp `Dockerfile`, thiếu file dependencies, hoặc lỗi mạng khi push), tiến trình dừng ngay lập tức và trả về `exit code != 0` (`failed`).

### A13. Dọn dẹp môi trường (Container Cleanup)
- Sau khi job kết thúc, Runner tự động huỷ bỏ và xóa hoàn toàn cả 2 container (`docker` chính và `docker-dind` service) cùng mạng ảo nội bộ.
- Do container DinD bị huỷ và môi trường là vô trạng thái (stateless), các image build tạm thời bị xóa khỏi runner; chỉ image đã được `docker push` thành công là tồn tại an toàn trên `registry.ftech.ai`.

### A14. Tác động tới Pipeline (Pipeline Gate)
- Job build được cấu hình `allow_failure: false`.
- **Nếu Job Build Failed:** Toàn bộ Pipeline lập tức chuyển sang trạng thái **Failed** và dừng lại. Stage `detect-secrets` cùng toàn bộ các stage sau đó bị **bỏ qua hoàn toàn (skipped)**.

---

## 4. PHẦN B: STAGE `detect-secrets` (QUÉT SECRET VÀ MÃ NHẠY CẢM)

*Stage này chạy sau khi Stage `build` đã hoàn thành thành công, chịu trách nhiệm quét tĩnh toàn bộ mã nguồn để phát hiện API Key, Private Key, Token, Password bị hard-code.*

### B5–B6. Runner nhận Job và Chuẩn bị Executor
- Khi Stage `build` trả về trạng thái `passed`, GitLab Server chuyển job `detect-secrets` sang trạng thái `pending`.
- Runner được gắn tag `[devsecops]` (cụm runner chuyên trách bảo mật) sẽ nhận job.
- **Mô hình Single Container:** Job chỉ khai báo `image:` mà **không** có `services:`, do đó Docker Executor chỉ cần tạo duy nhất **1 container đơn lẻ**, không cần Docker daemon và không tiêu tốn tài nguyên DinD.

### B7–B8. Tải Image và Khởi tạo Container
- Runner kéo image công cụ quét bảo mật chuyên dụng nội bộ:
  ```text
  registry.ftech.ai/public/is-chart/detect-secrets:v2.8
  ```
- Khởi tạo duy nhất 1 container độc lập từ image này để chuẩn bị thực thi phân tích mã nguồn.

### B9. Clone / Checkout mã nguồn độc lập (Fresh Checkout)
- Runner-helper thực hiện clone/checkout lại mã nguồn tại đúng commit SHA vào workspace của container bảo mật.
- Môi trường này hoàn toàn độc lập, tách biệt với container của stage build đã bị hủy ở bước trước.

### B10. Tiêm nạp biến môi trường và cấu hình loại trừ (Exclusions)
- Nạp các biến hệ thống mặc định của GitLab.
- Nạp các biến cấu hình loại trừ do dự án định nghĩa trong `.gitlab-ci.yml` (nếu có):
  - `EXCLUDE_SECRETS`: Chuỗi các secret giả lập hoặc chuỗi đã được duyệt ngoại lệ, ngăn cách bằng dấu `|` (ví dụ: `"token_test_123|dummy_password_abc"`).
  - `EXCLUDE_FOLDERS`: Danh sách các thư mục không quét, ngăn cách bằng dấu `;` (ví dụ: `"static;store/static;vendor;node_modules"`).

### B11. Thực thi phân tích bảo mật (Security Scan Script)
Container thực thi tập lệnh:

```sh
# 1. Xóa bỏ thư mục lịch sử Git
rm -rf .git/

# 2. Chạy công cụ phân tích quét secret
python /app/detect-secrets.py
```

- **Mục đích của `rm -rf .git/`:** Loại bỏ toàn bộ metadata và lịch sử commit cũ, chỉ giữ lại mã nguồn tại thời điểm hiện tại của commit. Việc này giúp:
  1. Tăng tốc độ quét lên nhiều lần.
  2. Tránh báo động giả (false positive) từ các chuỗi secret đã từng bị xoá trong lịch sử commit cũ.
- **Công cụ `detect-secrets.py`:** Quét toàn bộ file trong thư mục để tìm chuỗi nghi là secret/token/key. Cơ chế phát hiện cụ thể bên trong (entropy, regex, hay danh sách plugin nào) chưa được xác nhận vì source code không nằm trong phạm vi tài liệu — chỉ biết chắc công cụ đọc và loại trừ theo 2 biến `EXCLUDE_SECRETS`/`EXCLUDE_FOLDERS` (đã xác nhận qua README).

### B12. Thu thập Log và Đánh giá Exit Code
- Toàn bộ kết quả quét chi tiết (file, dòng code vi phạm, loại secret) được ghi vào log và stream về giao diện GitLab CI.
- **Nếu phát hiện Secret không nằm trong danh sách whitelist:** Script trả về `exit code != 0` ➔ Job nhận trạng thái **Failed**.
- **Nếu mã nguồn sạch (không có secret rò rỉ):** Script trả về `exit code = 0` ➔ Job nhận trạng thái **Passed**.

### B13. Dọn dẹp môi trường (Cleanup)
- Runner dọn dẹp và xóa container scanner.
- Vì job không khai báo `artifacts:`, không có file trung gian nào được lưu giữ trên GitLab server ngoài bản ghi console log.

### B14. Tác động tới Pipeline (DevSecOps Gate)
- Job `detect-secrets` có cấu hình nghiêm ngặt: `allow_failure: false`.
- **Nếu phát hiện Secret:** Pipeline dừng ngay lập tức. Toàn bộ các stage phía sau như `dependency-check` (quét lỗ hổng thư viện qua Trivy), `upload-bom` (đẩy lên Dependency-Track), và `sonarqube-check` **sẽ không được thực hiện**.

---

## 5. SO SÁNH ĐẶC TÍNH KỸ THUẬT GIỮA 2 STAGE

| Tiêu chí | Stage `build` | Stage `detect-secrets` |
| :--- | :--- | :--- |
| **Mục đích chính** | Đóng gói mã nguồn & push image lên Registry | Rà soát phát hiện secret/token/password rò rỉ |
| **Tag Runner** | `[build]` | `[devsecops]` |
| **Loại Container** | Multi-container (Docker-in-Docker - DinD) | Single Container độc lập |
| **Image sử dụng** | `docker:20.10.16` + `docker:20.10.16-dind` | `registry.ftech.ai/.../detect-secrets:v2.8` |
| **Quyền thực thi** | Đòi hỏi `privileged: true` để chạy Docker daemon | Container tiêu chuẩn không cần `privileged` |
| **Xử lý thư mục `.git`** | Giữ nguyên để phục vụ build/versioning | `rm -rf .git/` trước khi quét mã nguồn |
| **Cấu hình `allow_failure`**| `false` (Lỗi là dừng pipeline) | `false` (Phát hiện secret là dừng pipeline) |
| **Cơ chế kích hoạt** | Phụ thuộc nhánh (`only:` dev/staging/prod/tags) | Áp dụng rộng rãi cho mọi nhánh khi build pass |

---

## 6. CƠ CHẾ PHẢN HỒI VÀ QUY TRÌNH XỬ LÝ SỰ CỐ (FEEDBACK LOOP)

Khi một trong hai stage gặp sự cố (`Failed`), Developer theo dõi trên giao diện GitLab CI/CD và xử lý theo quy trình sau:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              QUY TRÌNH PHẢN HỒI VÀ XỬ LÝ SỰ CỐ (FEEDBACK LOOP)                          │
└───────────────────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                                    │
                             ┌──────────────────────┴──────────────────────┐
                             ▼                                             ▼
               [STAGE BUILD BỊ FAILED]                    [STAGE DETECT-SECRETS BỊ FAILED]
                             │                                             │
                             ▼                                             ▼
               ┌───────────────────────────┐                 ┌───────────────────────────┐
               │ Nguyên nhân:              │                 │ Phân loại rủi ro:         │
               │ • Dockerfile sai cú pháp  │                 ├───────────────────────────┤
               │ • Sai tài khoản Registry  │                 │ A. Secret thật:           │
               │ • Thiếu file dependencies │                 │    - Thu hồi / rotate key │
               │ • Đầy bộ nhớ / lỗi mạng   │                 │    - Đưa vào CI/CD Vars   │
               │ ───────────────────────── │                 │ B. False Positive:        │
               │ Khắc phục:                │                 │    - Thêm EXCLUDE_SECRETS │
               │ • Sửa Dockerfile / code   │                 │    - Thêm EXCLUDE_FOLDERS │
               │ • Kiểm tra cấu hình build │                 └─────────────┬─────────────┘
               └─────────────┬─────────────┘                               │
                             │                                             │
                             └──────────────────────┬──────────────────────┘
                                                    │
                                                    ▼
                                    [Developer Commit & Git Push lại]
                                                    │
                                                    ▼
                                 [GitLab tạo Pipeline MỚI chạy lại từ đầu]
```

1. **Trường hợp Stage `build` thất bại:**
   - **Nguyên nhân:** Lỗi cú pháp trong `Dockerfile`, thiếu file thư viện nguồn, sai thông tin tài khoản `REGISTRY_PUSH_USER`/`REGISTRY_PUSH_PASSWORD`, hoặc dung lượng Registry đầy.
   - **Khắc phục:** Đọc log chi tiết của job, sửa lỗi mã nguồn hoặc cấu hình build, sau đó commit và push lại.

2. **Trường hợp Stage `detect-secrets` thất bại:**
   - **Nếu là Secret thật bị rò rỉ:** Developer phải lập tức thu hồi/thay thế (rotate) secret bị lộ, xóa hoàn toàn giá trị khỏi mã nguồn, cấu hình lại giá trị thông qua GitLab CI/CD Variables hoặc Secret Management, sau đó commit và push lại.
   - **Nếu là Báo động giả (False Positive):** Khai báo giá trị hoặc đường dẫn thư mục vào biến `EXCLUDE_SECRETS` hoặc `EXCLUDE_FOLDERS` trong file `.gitlab-ci.yml` của dự án, sau đó commit và push lại.

3. **Nguyên tắc vòng lặp (Fresh Pipeline):**
   - Mỗi lần Developer push một commit mới, GitLab sẽ tạo ra một **Pipeline mới hoàn toàn độc lập**. Quy trình sẽ chạy lại từ đầu (từ giai đoạn khởi tạo, kiểm tra điều kiện nhánh, chạy lại Stage `build`, rồi mới đến Stage `detect-secrets`), đảm bảo tính toàn vẹn và an toàn tuyệt đối cho hệ thống trước khi chuyển sang các bước DevSecOps và CD tiếp theo.
