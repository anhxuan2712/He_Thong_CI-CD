# MÔ HÌNH VÀ KIẾN TRÚC VẬN HÀNH GITOPS (ARGOCD)

---

## CHƯƠNG I: TỔNG QUAN, BỐI CẢNH & NGUYÊN LÝ CỐT LÕI CỦA GITOPS

### 1.1. Bối cảnh chuyển đổi: Push-based CI/CD vs Pull-based GitOps

Trước khi áp dụng GitOps, quy trình triển khai phần mềm sử dụng mô hình **Push-based CI/CD**:
* Máy chủ CI (GitLab Runner / Jenkins) trực tiếp nắm giữ `kubeconfig` có quyền cao (`cluster-admin`) để chạy lệnh `kubectl apply` hoặc `helm upgrade`.
* **Rủi ro lớn:** Nếu pipeline bị tấn công, toàn bộ cụm K8s có nguy cơ bị xâm nhập. Khi xảy ra sự cố, kỹ sư sửa tay (`kubectl edit`) trực tiếp trên cluster gây ra hiện tượng **Lệch cấu hình (Configuration Drift)**, mất dấu vết kiểm toán và gây khó khăn lớn khi cần phục hồi thảm họa (Disaster Recovery).

**Giải pháp với mô hình Pull-based GitOps:**
Chuyển toàn bộ quyền thực thi vào bên trong cụm Kubernetes. Một Controller nội bộ (**ArgoCD**) đóng vai trò giám sát thường trực: lấy Git làm quy chuẩn duy nhất và tự động kéo (Pull) trạng thái mong muốn về áp dụng cho cụm.

```
[MÔ HÌNH CŨ: PUSH-BASED]
Developer ──► GitLab CI ──(Nắm giữ Kubeconfig)──► Chọc thẳng vào K8s Cluster
                                                   ❌ Nguy cơ lộ Kubeconfig / Lệch cấu hình

[MÔ HÌNH MỚI: PULL-BASED GITOPS]
Developer ──► GitLab CI ──► Harbor Registry ──► Git Manifest ◄──(Kéo tự động)── ArgoCD (Trong K8s)
             (Không cần quyền K8s)                            │                     │
                                                              └────── Sync & Heal ──┘
```

### 1.2. 4 Nguyên tắc cốt lõi theo tiêu chuẩn OpenGitOps

1. **Khai báo tường minh (Declarative):** Toàn bộ trạng thái mong muốn của hệ thống (Deployments, Services, Ingress, HPA, Config) đều được định nghĩa bằng mã nguồn (YAML / Helm Chart).
2. **Quản lý phiên bản & Bất biến (Versioned & Immutable):** Git là "Nguồn chân lý duy nhất" (Single Source of Truth), mọi thay đổi bắt buộc phải qua Git Commit / Merge Request, lưu vết 100% lịch sử.
3. **Kéo tự động (Pulled Automatically):** Agent K8s (ArgoCD) tự động kéo cấu hình đã được phê duyệt trên Git về thực thi, CI runner không cần quyền truy cập cluster.
4. **Tự đối soát & Phục hồi liên tục (Self-Healing):** ArgoCD chạy vòng lặp đối soát (Reconciliation Loop). Khi có can thiệp trực tiếp trái phép trên cụm K8s, hệ thống tự động phát hiện sai lệch (**OutOfSync**) và ghi đè phục hồi về đúng trạng thái trên Git (**Self-Heal**).

---

## CHƯƠNG II: KIẾN TRÚC TỔNG THỂ & QUY TRÌNH PHÁT HÀNH TỰ ĐỘNG (END-TO-END)

Chu trình phát hành được tự động hóa khép kín từ khâu Developer commit mã nguồn đến khi phiên bản mới chạy ổn định trên Kubernetes:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Developer    │ ────► │  GitLab CI/CD   │ ────► │ Harbor Registry │
│   Commit Code   │  (1)  │Build, Test, Push│  (2)  │ (registry.ftech)│
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
                              ┌──────────────────────────────┘ (3) Webhook báo Tag mới
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ARGOCD GITOPS ENGINE                             │
│                                                                             │
│ 1. argocd-image-updater : Bắt tag mới từ Harbor ──► (4) Commit tag vào Git  │
│ 2. Git Manifest Repo    : Lưu trữ Helm Poly v3 + values-{env}.yaml          │
│ 3. ArgoCD Controller    : (5) Tự động đối soát & Kéo cấu hình về K8s        │
│ 4. Vault & ExternalSec  : Cấp phát Image Pull Secret & Runtime Secret       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ (6) Triển khai & Tự phục hồi
┌─────────────────────────────────────────────────────────────────────────────┐
│                            KUBERNETES WORKLOADS                             │
│                 (Môi trường: Dev / Staging / Production)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Chi tiết 6 giai đoạn trong chu trình phát hành:
1. **Developer Push Code:** Lập trình viên đẩy mã nguồn tính năng mới lên GitLab.
2. **GitLab CI Pipeline:** Pipeline tự động chạy test, build Docker Image, gắn tag chuẩn hóa (ví dụ: `dev-2026-09-08_...`) và đẩy image lên Harbor Registry (`registry.ftech.ai`). Pipeline kết thúc tại đây, không can thiệp vào K8s.
3. **Harbor Webhook Trigger:** Harbor phát tín hiệu Webhook thông báo có Image Tag mới sang ArgoCD Image Updater.
4. **Tự động cập nhật Manifest (`argocd-image-updater`):** Image Updater đối chiếu regex của tag, tự động tạo commit ghi đè tag mới vào file cấu hình trên repo Git Manifest (`manifest/{project}.git`).
5. **ArgoCD Kéo & Đồng bộ (Reconciliation & Sync):** ArgoCD Application phát hiện commit mới trên Git Manifest, lập tức kích hoạt tiến trình triển khai xuống K8s cluster tương ứng.
6. **Bảo mật & Khởi chạy Runtime:** Pod mới khởi tạo sử dụng secret kéo ảnh (`regcred`) từ Harbor và tự động nạp secret ứng dụng từ **HashiCorp Vault** lúc runtime.

---

## CHƯƠNG III: THIẾT KẾ PHÂN TẦNG HỆ THỐNG ARGOCD & CẤU TRÚC DỰ ÁN

Hệ thống GitOps được thiết kế theo mô hình **Phân tầng hướng mô-đun (Hierarchical Modular GitOps)**, phân tách rõ ràng thành 2 luồng quản trị độc lập:

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

### 3.1. Luồng 1: Quản trị Vòng đời Ứng dụng & Phân quyền (Application Stream)
* **`argocd-install`:** Chứa manifest cài đặt lõi ArgoCD (Server, Repo Server, Controller, Redis, SSO Dex tích hợp GitLab đăng nhập nội bộ).
* **`argocd-appprojects`:** Thiết lập ranh giới bảo mật (**Logical Isolation Boundary**) cho từng khối dự án (ví dụ: `southeast-asia-game`, `webgl-game`, `fcloud`...). Giới hạn cluster đích, namespace đích, whitelist repo và phân quyền truy cập.
* **`argocd-apps/app-of-apps` (Root Application):** Áp dụng mô hình Parent-Child với cờ quét đệ quy (`directory.recurse: true`). Khi cần đưa một microservice/game mới lên hệ thống, kỹ sư chỉ cần commit 1 file YAML vào thư mục `argocd-apps/{project}/`, Root App sẽ **tự động phát hiện và kích hoạt ứng dụng lên K8s trong vài giây** mà không cần tạo thủ công trên Web UI.
* **`argocd-apps/{project}`:** Chứa các Application YAML chi tiết của từng service con (kèm cấu hình regex tự động bắt tag của `argocd-image-updater`).

### 3.2. Luồng 2: Quản trị Hạ tầng Nền tảng & Cấp phát Chứng thực (Infrastructure Stream)
* **`argocd-bootstrap-apps`:** Quản lý vòng đời các công cụ nền tảng cho toàn cụm: Vault Injector, External Secrets Operator (ESO), Ingress Controller, Cert-Manager...
* **`argocd-manifest-credential` & `argocd-image-updater-regcreds`:** Khởi tạo token kết nối Vault để ArgoCD đọc/ghi vào Git Manifest repo và cho phép Image Updater truy vấn API của Harbor.
* **`argocd-apps/regcred`:** Tự động hóa việc sinh secret kéo ảnh (`regcred`) vào từng Namespace trên mọi cluster K8s thông qua `ApplicationSet` kết hợp `ExternalSecrets`.

### 3.3. Chuẩn hóa Manifest qua Thư viện Helm Chart Poly v3
* Tách biệt 2 loại repo:
  * **GitOps Repo (`argocd.git`):** Quản lý điều phối, phân quyền và kết nối cụm (dành cho DevOps).
  * **Manifest Repo (`manifest/{project}.git`):** Quản lý tham số ứng dụng (CPU, RAM, Replicas, Ingress) (dành cho Developer).
* Toàn bộ microservice và game dùng chung thư viện **Helm Chart Poly v3**. Lập trình viên chỉ cần duy trì file `values-{env}.yaml` ngắn gọn (~20-30 dòng) thay vì viết hàng trăm dòng Kubernetes YAML thủ công, loại bỏ hoàn toàn các lỗi sai lệch cấu hình.

---

## CHƯƠNG IV: QUẢN TRỊ BẢO MẬT & CHIẾN LƯỢC "ZERO-SECRET IN GIT"

Hệ thống kiên quyết thực hiện nguyên tắc **Zero-Secret in Git**: Tuyệt đối không lưu trữ mật khẩu, API Key hay Token dạng Plain-text trên Git.

### 4.1. Phân biệt Bản chất 2 Tầng Secret trong Hệ thống (`regcred` vs `vault`)

Hệ thống phân tách rành mạch giữa **Secret hạ tầng để kéo ảnh container** và **Secret ứng dụng runtime**:

```
                              ┌──────────────────────────────────────────────────┐
                              │               HASHICORP VAULT                    │
                              │           (Kho Quản Trị Bí Mật)                  │
                              └─────────┬──────────────────────────────┬─────────┘
                                        │                              │
          Đường dẫn:                    │                              │  Đường dẫn:
          secret/data/projects/{prj}/   │                              │  secret/data/projects/{prj}/
          regcred                       │                              │  {service}/{env}
                                        ▼                              ▼
                         ┌─────────────────────────────┐┌─────────────────────────────┐
                         │  External Secrets Operator  ││    Vault Agent Injector     │
                         └──────────────┬──────────────┘└──────────────┬──────────────┘
                                        │                              │
                               Sinh K8s │                              │ Ghi trực tiếp vào
                               Secret   │                              │ RAM Disk (/vault/secrets)
                                        ▼                              ▼
                         ┌─────────────────────────────┐┌─────────────────────────────┐
                         │  Kubelet / Worker Node      ││   Container Pod Runtime     │
                         │ (Dùng để Pull Docker Image) ││(Dùng kết nối DB, Redis, API)│
                         └─────────────────────────────┘└─────────────────────────────┘
```

| Tiêu chí | 1️⃣ Image Pull Secret (`regcred`) | 2️⃣ Application Runtime Secret (`vault`) |
|---|---|---|
| **Bản chất** | Kubernetes Secret kiểu `kubernetes.io/dockerconfigjson`. | Secret cấu hình ứng dụng (DB Password, Redis Auth, JWT Key...). |
| **Mục đích** | Cho Kubelet Node đăng nhập Harbor để **kéo Image container** về máy chủ. | Cho ứng dụng bên trong Pod **kết nối Database, Third-party API**. |
| **Phạm vi quản lý** | Cấp độ toàn Namespace (**Namespace Scope**). | Cấp độ từng Pod / Microservice (**Pod Scope**). |
| **Cơ chế nạp** | Tự động sinh qua **External Secrets Operator (ESO)**. | Tự động inject qua **Vault Agent Injector (Sidecar)**. |
| **Đối tượng dùng** | **Tất cả các Pod** trong namespace (được Helm Poly v3 gán tự động). | **Chỉ các ứng dụng Backend/API** có nhu cầu kết nối DB/Bảo mật. |

### 4.2. Cơ chế Cấp phát Image Pull Secret (`regcred`)
* Tài khoản Robot Account của Harbor được lưu trữ an toàn trong Vault.
* `ExternalSecret` định kỳ đối soát với Vault, tự động tạo và duy trì K8s Secret `regcred` trong từng namespace.
* Helm Chart Poly v3 tự động gán `imagePullSecrets: [{name: "regcred"}]` vào cấu hình Pod. Kubelet tự động kéo được Image từ Harbor mà lập trình viên không cần cấu hình secret thủ công.

### 4.3. Cơ chế Inject Secret động cấp Pod (`vault`)
* Đối với ứng dụng Backend/API, thông tin kết nối DB và API Key không lưu trong ConfigMap.
* **Vault Mutating Webhook** tự động gắn một container sidecar (`vault-agent`) vào Pod lúc khởi chạy.
* Sidecar xác thực với Vault qua ServiceAccount Token của Kubernetes, lấy Secret và ghi trực tiếp vào ổ đĩa bộ nhớ RAM ảo (**ramfs memory** tại `/vault/secrets/config.env`).
* Secret chỉ tồn tại trong bộ nhớ RAM của Pod, **không bao giờ bị ghi xuống ổ đĩa cứng hay lưu thô trên Kubernetes etcd**.

### 4.4. Phân tích Ca sử dụng Thực tế: WebGL Game vs Backend Microservice
* **Game WebGL / HTML5 Canvas (vd: `c108-jigsaw-anime-girl`):** Là ứng dụng tĩnh chạy hoàn toàn phía Client (trình duyệt người dùng) kết hợp Web Server Nginx. Ứng dụng không kết nối Database nội bộ, không có Secret backend $\rightarrow$ **Không kích hoạt module Vault**, giúp tiết kiệm tài nguyên CPU/RAM cho cluster vì không cần chạy sidecar container.
* **Backend Microservices (Auth, Payment, Game Server, API):** Bắt buộc kích hoạt khối `vault:` trong manifest để bảo vệ dữ liệu nhạy cảm.

### 4.5. Cơ chế Phân quyền RBAC qua Casbin Policy
* Phân quyền 2 tầng: Tầng toàn cục (`argocd-rbac-cm` kết hợp GitLab SSO) và Tầng từng dự án (`AppProject`).
* Phân chia 3 nhóm quyền chính:
  * **`read-only` (QA/Tester):** Chỉ xem thông tin tài nguyên, logs và sự kiện.
  * **`developer` (Dev):** Xem, Sync và Restart Pod trên môi trường Dev/Staging để kiểm thử tính năng mới.
  * **`admin / lead` (Tech Lead/DevOps):** Toàn quyền kiểm soát và phê duyệt triển khai môi trường Production.

---

## CHƯƠNG V: KẾT LUẬN & ĐỀ XUẤT TỐI ƯU HÓA

### 5.1. Tóm tắt Giá trị Đạt được
1. **Tự động hóa khép kín:** Khắc phục hoàn toàn sự phụ thuộc vào thao tác thủ công, loại bỏ nguy cơ lệch cấu hình (Configuration Drift) nhờ tính năng Self-Healing.
2. **Bảo mật Zero-Trust:** Pipeline CI không còn nắm giữ Kubeconfig; toàn bộ Secret được quản trị tập trung tại Vault và cấp phát tự động.
3. **Chuẩn hóa hạ tầng:** Tái sử dụng Helm Library Poly v3 và mô hình App-of-Apps, giúp việc onboarding dịch vụ mới diễn ra nhanh chóng, chính xác.

### 5.2. Đề xuất Lộ trình Nâng cấp Tiếp theo
1. **Nghiên cứu áp dụng Progressive Delivery (Argo Rollouts):** Có thể cân nhắc triển khai chiến lược Canary Release nhằm phân luồng lưu lượng truy cập theo từng giai đoạn và tự động kích hoạt Rollback tức thời nếu phát hiện tỷ lệ lỗi dịch vụ (HTTP 5xx, latency) vượt ngưỡng cho phép.
2. **Tích hợp ChatOps (ArgoCD Notifications):** Có thể mở rộng tích hợp cơ chế tự động gửi thông báo trạng thái đồng bộ và cảnh báo sự cố Pod (`CrashLoopBackOff`, `Degraded`) về kênh liên lạc nội bộ (Telegram/Slack) của từng nhóm phát triển để hỗ trợ phản ứng nhanh.
