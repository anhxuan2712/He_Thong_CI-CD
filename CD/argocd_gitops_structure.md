### **Câu 1: Cấu trúc gitops argocd**

Dựa trên sơ đồ bạn cung cấp và toàn bộ cấu trúc thực tế của repository `argocd`, hệ thống GitOps của FTech được thiết kế theo mô hình **Phân tầng hướng mô-đun (Hierarchical Modular GitOps)** kết hợp kiến trúc **App-of-Apps** và **Zero-Secret in Git** (thông qua Vault & ExternalSecrets).

Dưới đây là giải thích chi tiết toàn bộ kiến trúc từ hạ tầng đến ứng dụng:

---

```
                                    ┌────────────────────────────────────────────────────────┐
                                    │               HỆ THỐNG GITOPS ARGOCD                   │
                                    └────────────────────────────────────────────────────────┘
                    [ LUỒNG 1: QUẢN TRỊ ỨNG DỤNG & RBAC ]              [ LUỒNG 2: HẠ TẦNG & BẢO MẬT CREDENTIALS ]
                                       │                                                  │
                                       ▼                                                  ▼
                       ┌───────────────────────────────┐                  ┌───────────────────────────────┐
                       │        argocd-install         │                  │     argocd-bootstrap-apps     │
                       │  (Cài đặt ArgoCD Core Engine) │                  │  (Thành phần hạ tầng nền tảng)│
                       └───────────────┬───────────────┘                  └───────────────┬───────────────┘
                                       │                                                  │
                                       ▼                                          ┌───────┴───────┐
                       ┌───────────────────────────────┐                          ▼               ▼
                       │      argocd-appprojects       │            ┌───────────────────┐   ┌───────────────────────────┐
                       │(Ranh giới bảo mật, RBAC Casbin│            │argocd-image-      │   │ argocd-manifest-credential│
                       │ Destination & SourceRepo)     │            │updater-regcreds   │   │(Token kéo Manifest Git)   │
                       └───────────────┬───────────────┘            │(Token đọc Registry│   └───────────────────────────┘
                                       │                            │ tag mới từ Harbor)│
                                       ▼                            └───────────────────┘
                       ┌───────────────────────────────┐                          │
                       │   argocd-apps/app-of-apps     │                          ▼
                       │ (Root App quản lý quét đệ quy)│                  ┌───────────────────────────────┐
                       └───────────────┬───────────────┘                  │      argocd-apps/regcred      │
                                       │                                  │ (Secret kéo Image cho từng    │
                                       ▼                                  │  Namespace & Cluster qua Vault│
                       ┌───────────────────────────────┐                  └───────────────┬───────────────┘
                       │     argocd-apps/{project}     │                                  │
                       │(Application YAML chi tiết của │◄─────────────────────────────────┘
                       │ từng Service + Image Updater) │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │                      Manifest Repo                       │
                       │  (gitlab.ftech.ai/devops/gitops/argocd/manifest/{project})│
                       │       [Helm Chart Poly v3 + values-*.yaml]               │
                       └──────────────────────────────────────────────────────────┘
```

---

## 1. Luồng 1: Quản trị Vòng đời Ứng dụng & Phân quyền RBAC (Trục bên trái)

### 🔹 `argocd-install` (Cài đặt ArgoCD Core)
* **Vai trò:** Khởi tạo bộ máy ArgoCD trên cụm K8s chính (Server, Repo Server, Controller, Redis, Dex SSO...).
* Cấu hình SSO tích hợp với GitLab của công ty để nhân viên đăng nhập qua tài khoản nội bộ.

### 🔹 `argocd-appprojects` (Định nghĩa Ranh giới Dự án & Phân quyền)
* **Vai trò:** Thiết lập **Logical Boundary** (vùng cô lập) cho từng dự án (như `southeast-asia-game`, `webgl-game`, `fcloud`, `fedu`...).
* **Nhiệm vụ chính:**
  1. **Bảo mật & RBAC Casbin Policy:** Định nghĩa cụ thể User/Group nào (vd: `gianglt@ftech.com.vn`) có quyền gì (`view`, `sync`, `restart`, `update`, `admin`) trên app nào.
  2. **Destinations Whitelist:** Chỉ cho phép project deploy vào đúng Cluster/Namespace quy định (vd: `dev-new`, `prod`).
  3. **Source Repos Whitelist:** Giới hạn chỉ được kéo mã nguồn từ repo GitOps và Manifest hợp lệ.
  4. **Resource Blacklist:** Ngăn chặn việc tạo đè các resource nhạy cảm của cluster (như `ClusterRole`, `RoleBinding`).

### 🔹 `argocd-apps/app-of-apps` (Mô hình App-of-Apps Parent)
* **Vai trò:** Tạo ra một **Root Application** cho mỗi dự án.
* Sử dụng cờ `directory.recurse: true` trỏ vào thư mục `argocd-apps/{project}/`.
* Khi bạn tạo mới bất kỳ file yaml nào trong thư mục project con, Root App sẽ tự động phát hiện và kích hoạt ứng dụng đó lên ArgoCD mà không cần khai báo thủ công trên UI.

### 🔹 `argocd-apps/{project}` (Các Application YAML con)
* **Vai trò:** Định nghĩa chi tiết từng Microservice/Game/API cụ thể (vd: `flay-auth-dev.yaml`, `fqa-appchat-prod.yaml`).
* **Các thành phần tích hợp trong file này:**
  * **Trỏ tới Helm Manifest:** Trỏ sang repo manifest tương ứng với đường dẫn chart và file cấu hình môi trường (`values-dev.yaml`, `values-prod.yaml`).
  * **Cấu hình ArgoCD Image Updater:** Tự động lắng nghe Registry, khi CI/CD build xong image mới khớp với regex (vd: `^dev-[0-9]{4}-...`), Image Updater sẽ tự động ghi đè tag mới vào Git.
  * **Sync Policy:** Cấu hình cơ chế tự động đồng bộ (`selfHeal`, `prune`, `CreateNamespace`).

---

## 2. Luồng 2: Quản lý Hạ tầng, Chứng thực & Bảo mật (Trục bên phải)

### 🔹 `argocd-bootstrap-apps` (Infra Components)
* **Vai trò:** Khởi tạo và quản lý vòng đời của các công cụ nền tảng cho toàn bộ cụm K8s:
  * **Vault Injector / External Secrets:** Cầu nối lấy secret từ HashiCorp Vault.
  * **ArgoCD Image Updater:** Công cụ tự động quét và cập nhật image tag.
  * **Ingress-Nginx, Cert-Manager, Monitoring:** Hệ thống mạng, chứng chỉ SSL và giám sát.

### 🔹 `argocd-manifest-credential` & `argocd-image-updater-regcreds`
* **`argocd-manifest-credential`:** Khởi tạo Secret/Token (kết nối với Vault) để ArgoCD có quyền đọc/ghi vào các Git Manifest Repo riêng tư trên `gitlab.ftech.ai`.
* **`argocd-image-updater-regcreds`:** Cung cấp thông tin chứng thực (Robot Account) để Image Updater có thể kiểm tra danh sách tag mới trên `registry.ftech.ai`.

### 🔹 `argocd-apps/regcred` (Registry Credentials per Environment/Cluster)
* **Vai trò:** Quản lý việc cấp phát Secret kéo Image (`dockerconfigjson`) vào **từng Namespace trên từng Cluster K8s**.
* **Cơ chế:** Sử dụng `ApplicationSet` kết hợp `ExternalSecrets` để tự động kéo `robot$pull` từ Vault và tạo ra Kubernetes Secret (vd: `pullsecret:argocd/southeast-asia-game-regcred`). Nhờ đó, K8s Node có thể pull image từ Harbor mà không bị lỗi `ImagePullBackOff`.

---

## 3. Lớp cuối cùng: Manifest Repo (`gitlab.ftech.ai/.../manifest/{project}`)

* **Vai trò:** Là kho lưu trữ **Manifest thực tế** (thường là Helm Chart chuẩn hóa như `Poly v3` và các file `values-*.yaml`).
* **Điểm tách biệt cốt lõi:**
  * Repo `argocd` (repo hiện tại bạn đang đứng): Chỉ quản lý **Cấu hình điều phối GitOps & Phân quyền**.
  * Repo `manifest/{project}`: Quản lý **Tham số runtime của ứng dụng** (CPU, RAM, Replicas, Ingress Domain, Env, Vault Config).

---

## 4. Tóm tắt Luồng hoạt động End-to-End khi Deploy một App

1. **Dev commit code ứng dụng** $\rightarrow$ GitLab CI build Docker Image và đẩy lên `registry.ftech.ai` với tag mới (vd: `dev-2026-09-06_...`).
2. **ArgoCD Image Updater** (được cấp quyền qua `argocd-image-updater-regcred`) phát hiện tag mới $\rightarrow$ Tự động commit tag mới vào repo `manifest/{project}`.
3. **ArgoCD Application** (thuộc `argocd-apps/{project}`) phát hiện commit mới trên repo Manifest $\rightarrow$ Tự động Trigger Sync xuống Kubernetes Cluster (`dev-new`).
4. **Kubernetes Cluster**:
   * Dùng `regcred` (do luồng `argocd-apps/regcred` tạo) để kéo image từ Harbor.
   * Dùng `vault-injector` (do luồng `argocd-bootstrap-apps` cài đặt) để inject secret an toàn từ Vault vào trong container lúc khởi chạy.
5. **AppProject** đảm bảo chỉ những user được gán quyền (như `gianglt@ftech.com.vn`) mới có thể thao tác (View/Sync/Restart) với app trên giao diện ArgoCD.
