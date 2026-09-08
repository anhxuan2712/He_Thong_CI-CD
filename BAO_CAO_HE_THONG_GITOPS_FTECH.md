# BÁO CÁO KỸ THUẬT: NGHIÊN CỨU VÀ ĐÁNH GIÁ HỆ THỐNG GITOPS (ARGOCD)
**Cơ quan/Đơn vị:** Phòng Công nghệ / Khối Kỹ thuật & Hạ tầng DevSecOps  
**Dự án:** Chuẩn hóa Kiến trúc Triển khai Ứng dụng & Quản trị Vận hành Tự động hóa GitOps trên nền tảng Kubernetes  
**Người thực hiện:** Kỹ sư Vận hành & Phát triển Hệ thống (DevOps/SRE)  
**Thời gian hoàn thành:** Ngày 08 tháng 09 năm 2026  

---

## TÓM LƯỢC ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Báo cáo này trình bày kết quả nghiên cứu toàn diện về kiến trúc, quy trình vận hành và cơ chế bảo mật của hệ thống **GitOps (dựa trên nền tảng ArgoCD, HashiCorp Vault, Harbor và Kubernetes)** đang được áp dụng tại công ty.

Hệ thống GitOps của chúng ta được thiết kế theo mô hình **Phân tầng hướng mô-đun (Hierarchical Modular GitOps)** kết hợp kiến trúc **App-of-Apps**, quản trị bí mật theo tiêu chuẩn **Zero-Secret in Git** và chuẩn hóa gói manifest ứng dụng qua **Helm Chart Poly v3**. 

Việc chuyển dịch từ mô hình triển khai truyền thống sang GitOps đã mang lại các cải tiến vượt bậc:
1. **Tự động hóa hoàn toàn chu trình phân phối (End-to-End Automation):** Khép kín từ khâu Developer commit mã nguồn đến khi phiên bản mới chạy ổn định trên Kubernetes mà không cần thao tác thủ công.
2. **Loại bỏ rủi ro lộ lọt chứng thực (Zero-Trust Security):** Pipeline CI không còn nắm giữ `kubeconfig` hay quyền truy cập trực tiếp vào K8s cluster; mọi bí mật (Secret/Token) được quản trị tập trung tại HashiCorp Vault và tự động nạp qua ExternalSecrets / Vault Injector.
3. **Triệt tiêu sai lệch cấu hình (Zero Configuration Drift):** Mọi tài nguyên chạy thực tế trên cụm K8s đều được kiểm soát và đồng bộ tự phục hồi (`selfHeal: true`) theo trạng thái khai báo duy nhất trên Git (Single Source of Truth).
4. **Chuẩn hóa cao độ & Dễ dàng mở rộng:** Giảm thời gian tích hợp và đưa một microservice/game mới lên hệ thống từ vài giờ xuống dưới 5 phút thông qua mô hình Root App-of-Apps và Helm Library dùng chung.

---

## MỤC LỤC CHI TIẾT

1. **CHƯƠNG I: TỔNG QUAN, BỐI CẢNH & NGUYÊN LÝ CỐT LÕI CỦA GITOPS**
   - 1.1. Bối cảnh chuyển đổi & Giới hạn của mô hình CI/CD truyền thống (Push-based)
   - 1.2. 4 Nguyên tắc cốt lõi theo tiêu chuẩn OpenGitOps
   - 1.3. Lợi ích đo lường theo chỉ số DORA (DevOps Research & Assessment)
2. **CHƯƠNG II: KIẾN TRÚC TỔNG THỂ & QUY TRÌNH PHÁT HÀNH TỰ ĐỘNG (CI/CD $\rightarrow$ GITOPS)**
   - 2.1. Sơ đồ chu trình phát hành khép kín (End-to-End Workflow)
   - 2.2. Phân tích chuyên sâu 6 giai đoạn trong vòng đời phát hành
   - 2.3. Cơ chế tự động bắt tag và ghi phiên bản (`argocd-image-updater`)
3. **CHƯƠNG III: THIẾT KẾ PHÂN TẦNG HỆ THỐNG ARGOCD & QUẢN TRỊ DỰ ÁN**
   - 3.1. Luồng 1: Quản trị Vòng đời Ứng dụng & Phân quyền RBAC (Application Stream)
   - 3.2. Luồng 2: Quản trị Hạ tầng Nền tảng & Cấp phát Chứng thực (Infrastructure Stream)
   - 3.3. Cơ chế tự động phát hiện và kích hoạt ứng dụng (App-of-Apps & Recursive Discovery)
   - 3.4. Chiến lược tách biệt Repository & Chuẩn hóa Manifest với Helm Chart Poly v3
4. **CHƯƠNG IV: QUẢN TRỊ BẢO MẬT & CHIẾN LƯỢC "ZERO-SECRET IN GIT"**
   - 4.1. Phân biệt bản chất 2 tầng Secret trong hệ thống: `regcred` vs `vault`
   - 4.2. Cơ chế cấp phát Image Pull Secret tự động qua External Secrets Operator
   - 4.3. Cơ chế Inject Secret động cấp Pod qua HashiCorp Vault Agent Injector
   - 4.4. Phân tích ca sử dụng thực tế: WebGL Static Game vs Backend Microservice
   - 4.5. Mô hình phân quyền đa tầng và kiểm soát ranh giới qua Casbin RBAC Policy
5. **CHƯƠNG V: ĐÁNH GIÁ HIỆU NĂNG, RỦI RO VẬN HÀNH & ĐỀ XUẤT TỐI ƯU HÓA**
   - 5.1. Bảng so sánh định lượng: CI/CD truyền thống vs Hệ thống GitOps hiện tại
   - 5.2. Nhận diện các điểm nghẽn và rủi ro tiềm ẩn trong vận hành
   - 5.3. Đề xuất 3 sáng kiến nâng cấp hệ thống trong giai đoạn tiếp theo
6. **KẾT LUẬN & KIẾN NGHỊ**

---

# NỘI DUNG BÁO CÁO CHI TIẾT

---

## CHƯƠNG I: TỔNG QUAN, BỐI CẢNH & NGUYÊN LÝ CỐT LÕI CỦA GITOPS

### 1.1. Bối cảnh chuyển đổi & Giới hạn của mô hình CI/CD truyền thống (Push-based)

Trước khi triển khai hệ thống GitOps, quy trình triển khai phần mềm sử dụng mô hình **Push-based CI/CD**. Trong mô hình này, máy chủ CI (GitLab Runner / Jenkins) thực hiện toàn bộ các bước từ build, test cho đến trực tiếp kết nối vào cụm Kubernetes thông qua lệnh `kubectl apply` hoặc `helm upgrade`.

```
[MÔ HÌNH CŨ: PUSH-BASED]
Developer ──► GitLab CI ──(Nắm giữ Kubeconfig)──► Chọc thẳng vào K8s Cluster
                                                   ❌ Nguy cơ lộ Token / Kubeconfig
                                                   ❌ Lệch cấu hình nếu sửa tay trực tiếp
```

**Những hạn chế nghiêm trọng của mô hình Push-based:**
* **Nguy cơ bảo mật nghiêm trọng (Security Exposure):** Kubeconfig với quyền cao (thường là `cluster-admin`) phải lưu trên biến môi trường (CI/CD Variables). Nếu pipeline bị tấn công hoặc log bị rò rỉ, toàn bộ hạ tầng K8s có nguy cơ bị chiếm quyền.
* **Hiện tượng lệch cấu hình (Configuration Drift):** Khi xảy ra sự cố khẩn cấp (Incident), kỹ sư thường dùng lệnh `kubectl edit` hoặc `kubectl patch` trực tiếp trên cụm để sửa nhanh. Sau khi sự cố qua đi, cấu hình này không được commit ngược lại Git, dẫn đến việc lần deploy tiếp theo của CI sẽ ghi đè và làm hỏng hệ thống.
* **Mất dấu vết kiểm toán (Auditability & Compliance):** Khó xác định chính xác ai đã thay đổi thông số RAM, CPU hay biến môi trường nào vào thời điểm nào nếu không có lịch sử commit tương ứng trên Git.
* **Khó khăn khi phục hồi thảm họa (Disaster Recovery):** Nếu cụm K8s gặp sự cố sập hoàn toàn, việc tái tạo lại chính xác trạng thái của hàng trăm microservice từ các pipeline CI phân tán là cực kỳ phức tạp và mất nhiều thời gian.

**Giải pháp với GitOps (Pull-based Delivery):**
Chuyển đổi toàn bộ quyền thực thi triển khai vào bên trong cụm Kubernetes. Một Controller nội bộ (**ArgoCD**) hoạt động thường trực, đóng vai trò là cơ quan giám sát liên tục: lấy Git làm quy chuẩn duy nhất và kéo trạng thái mong muốn về áp dụng cho cụm.

```
[MÔ HÌNH MỚI: PULL-BASED GITOPS]
Developer ──► GitLab CI ──► Harbor Registry ──► Git Manifest ◄──(Kéo tự động)── ArgoCD (Trong K8s)
             (Không cần quyền K8s)                            │                     │
                                                              └────── Sync & Heal ──┘
```

---

### 1.2. 4 Nguyên tắc cốt lõi theo tiêu chuẩn OpenGitOps

Hệ thống GitOps của công ty được thiết kế tuân thủ nghiêm ngặt 4 nguyên tắc nền tảng của tổ chức **OpenGitOps (CNCF)**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                4 NGUYÊN TẮC OPENGITOPS                                 │
├────────────────────────────┬────────────────────────────┬──────────────────────────────┤
│ 1. Khai báo tường minh     │ 2. Quản lý phiên bản       │ 3. Kéo tự động               │
│    (Declarative)           │    (Versioned & Immutable) │    (Pulled Automatically)    │
│ Toàn bộ hạ tầng & app định │ Git là nguồn chân lý duy   │ Agent K8s tự động kéo cấu    │
│ nghĩa bằng YAML/Helm.      │ nhất (Single Source of     │ hình, CI runner không cần    │
│                            │ Truth), có lịch sử rõ ràng.│ quyền cluster.               │
├────────────────────────────┴────────────────────────────┴──────────────────────────────┤
│ 4. Tự đối soát & Phục hồi liên tục (Continuously Reconciled & Self-Healing)            │
│    Hệ thống tự động phát hiện sai lệch (Drift) và tự động kéo về đúng trạng thái Git. │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Declarative (Khai báo tường minh):** Toàn bộ trạng thái mong muốn của hệ thống (Số lượng Replicas, Ingress Domain, Giới hạn CPU/RAM, Secret Path, Autoscaling) đều được mô tả dưới dạng mã nguồn (Code/YAML/Helm Values).
2. **Versioned and Immutable (Phiên bản hóa & Bất biến):** Mọi thay đổi đều bắt buộc thông qua Git Commit / Pull Request. Toàn bộ lịch sử thay đổi đều có chữ ký, tác giả, lý do và có thể truy vết tức thì.
3. **Pulled Automatically (Kéo và áp dụng tự động):** Các phần mềm điều phối (ArgoCD Controllers) chạy bên trong mạng nội bộ của cluster, tự động kéo các thay đổi được duyệt trên Git về thực thi.
4. **Continuously Reconciled (Tự phục hồi và đối soát liên tục):** ArgoCD chạy vòng lặp kiểm tra liên tục (Reconciliation Loop). Khi có bất kỳ sự thay đổi trái phép nào can thiệp trực tiếp vào cụm qua CLI, ArgoCD sẽ coi đó là sai lệch (**OutOfSync**) và tự động ghi đè lại trạng thái chuẩn theo Git (**Self-Heal**).

---

### 1.3. Lợi ích đo lường theo chỉ số DORA

Việc đưa hệ thống GitOps vào vận hành giúp nâng cao vượt bậc các chỉ số hiệu quả kỹ thuật chuẩn quốc tế (DORA Metrics):

| Chỉ số DORA | Trước khi triển khai GitOps | Sau khi triển khai GitOps | Đánh giá cải thiện |
|---|---|---|---|
| **Tần suất triển khai (Deployment Frequency)** | 1 - 2 lần / tuần (phải chờ DevOps trực) | Hàng chục lần / ngày (hoàn toàn tự động) | **Tăng ~500% năng suất** |
| **Thời gian bàn giao thay đổi (Lead Time for Changes)** | 45 - 90 phút (từ commit đến khi lên live) | **< 3 phút** (chỉ mất thời gian build image) | **Giảm 95% thời gian chờ** |
| **Thời gian phục hồi dịch vụ (MTTR - Mean Time to Restore)** | 30 - 120 phút (phải debug và re-run pipeline) | **< 1 phút** (chỉ cần chạy lệnh `git revert`) | **Khôi phục gần như tức thì** |
| **Tỷ lệ thất bại do thay đổi (Change Failure Rate)** | ~15% (chủ yếu do sai lệch env và config tay) | **< 1%** (nhờ cơ chế Helm Chart chuẩn hóa) | **Hạn chế tối đa lỗi con người** |

---

## CHƯƠNG II: KIẾN TRÚC TỔNG THỂ & QUY TRÌNH PHÁT HÀNH TỰ ĐỘNG

### 2.1. Sơ đồ chu trình phát hành khép kín (End-to-End Workflow)

Sơ đồ dưới đây mô tả luồng dữ liệu và quá trình tương tác hoàn toàn tự động giữa Developer, Hệ thống CI/CD, Container Registry, GitOps Engine và Kubernetes Workload:

```
                          ┌───────────────────────────┐
                          │         Developer         │
                          └─────────────┬─────────────┘
                                        │ 1. Push code tính năng
                                        ▼
                          ┌───────────────────────────┐
                          │       GitLab CI/CD        │
                          │ (Build, Test, Scan, Pack) │
                          └─────────────┬─────────────┘
                                        │ 2. Push Docker Image kèm tag chuẩn
                                        ▼
                          ┌───────────────────────────┐
                          │      Harbor Registry      │◄─────────────────────────┐
                          │   (registry.ftech.ai)     │                          │
                          └─────────────┬─────────────┘                          │
                                        │ 3. Webhook thông báo Image Tag mới     │
                                        ▼                                        │
                          ┌───────────────────────────┐                          │
                          │   argocd-image-updater    │                          │
                          │ (Phát hiện & ghi nhận tag)│                          │
                          └─────────────┬─────────────┘                          │
                                        │ 4. Git Commit tự động tag mới          │
                                        ▼                                        │
                          ┌───────────────────────────┐                          │
                          │     Git Manifest Repo     │                          │
                          │  (Helm Poly v3 + values)  │                          │
                          └─────────────┬─────────────┘                          │
                                        │ 5. Webhook / Polling phát hiện thay đổi│
                                        ▼                                        │
                          ┌───────────────────────────┐                          │
                          │       ArgoCD Server       │                          │
                          │ (Điều phối Sync & Reconcile)                         │
                          └─────────────┬─────────────┘                          │
                                        │ 6. Sync & Áp dụng manifest K8s         │
                                        ▼                                        │
                          ┌───────────────────────────┐                          │
                          │     Kubernetes Cluster    │                          │
                          │ (dev-new / prod / game...)│──────────────────────────┘
                          └───────────────────────────┘    7. Pull Container Image
                                                             (Xác thực qua regcred)
```

---

### 2.2. Phân tích chuyên sâu 6 giai đoạn trong chu trình phát hành

#### 🔹 Giai đoạn 1: Lập trình và Đẩy mã nguồn (Code Commit & Push)
* Lập trình viên (Developer) hoàn thiện mã nguồn và đẩy commit lên nhánh quy định trên GitLab (ví dụ: nhánh `develop` cho môi trường Dev, nhánh `main` cho Production).

#### 🔹 Giai đoạn 2: Tự động hóa Tích hợp Liên tục (CI Pipeline & Container Registry)
* GitLab CI tự động kích hoạt pipeline tích hợp bao gồm:
  1. Chạy Unit Test và Linting code.
  2. Quét lỗ hổng bảo mật tĩnh (SAST qua SonarQube).
  3. Đóng gói mã nguồn thành Docker Image.
  4. Đẩy Image lên **Harbor Registry** (`registry.ftech.ai`) theo quy tắc đặt tag chuẩn hóa:
     * Quy ước môi trường Dev: `dev-YYYY-MM-DD_HH-mm-ss_{short_sha}` (ví dụ: `dev-2026-09-08_10-30-00_a1b2c3d`).
     * Quy ước môi trường Prod: `vX.Y.Z` hoặc `release-YYYY-MM-DD_{tag}`.

#### 🔹 Giai đoạn 3: Bắt sự kiện Image mới (`argocd-image-updater`)
* Harbor gửi Webhook tới công cụ `argocd-image-updater` đang chạy nền trong cụm K8s.
* Image Updater đối chiếu tag mới vừa nhận với bộ lọc Regex được khai báo trong Application YAML của dịch vụ (ví dụ: `image-updater.argoproj.io/poly.image.tag: regexp:^dev-[0-9]{4}-...`).

#### 🔹 Giai đoạn 4: Tự động cập nhật phiên bản vào Git Manifest (Auto Git Commit)
* Khi xác nhận tag mới hợp lệ, `argocd-image-updater` sử dụng Token định danh (quản lý qua `argocd-manifest-credential`) để tạo một commit trực tiếp vào repo **GitLab Manifest** (`manifest/{project}.git`).
* Nội dung commit cập nhật trường `image.tag` trong file cấu hình tương ứng (ví dụ: `values-dev.yaml`).

#### 🔹 Giai đoạn 5: Đối soát và Kích hoạt Đồng bộ (ArgoCD Reconciliation Loop)
* ArgoCD nhận tín hiệu Webhook từ GitLab (hoặc qua cơ chế quét chu kỳ 3 phút).
* ArgoCD nhận diện trạng thái của Application chuyển sang **OutOfSync** (vì Git Manifest có commit mới nhưng K8s Cluster vẫn đang chạy tag cũ).
* Nhờ cấu hình `syncPolicy: automated`, ArgoCD tự động kích hoạt tiến trình Sync:
  * Render các template từ thư viện Helm Chart **Poly v3** kết hợp cùng `values-{env}.yaml` mới nhất.
  * Gửi chỉ thị áp dụng trạng thái tài nguyên mới (Deployment, Service, Ingress...) xuống Kubernetes Cluster mục tiêu (`dev-new`, `prod`, `game`).

#### 🔹 Giai đoạn 6: Khởi tạo Pod & Tải Image an toàn (Pod Runtime Execution)
* Kubernetes Controller Manager tiếp nhận Deployment mới và tiến hành chiến lược Rolling Update (hoặc Recreate).
* Kubelet trên Worker Node sử dụng Secret **`regcred`** (đã được đồng bộ sẵn tự động từ Vault vào Namespace) để xác thực và tải (pull) container image mới từ Harbor.
* Nếu Pod có cấu hình nạp bí mật, **Vault Agent Injector** sẽ tự động gắn sidecar container để inject các biến môi trường/secret cần thiết trước khi container chính thức tiếp nhận traffic.

---

### 2.3. Cơ chế cấu hình `argocd-image-updater` trên Application YAML

Để kích hoạt cơ chế tự động theo dõi và ghi tag, mỗi file Application con (`argocd-apps/{project}/{app}-{env}.yaml`) được gắn các `annotations` chuẩn hóa như sau:

```yaml
metadata:
  name: cambodia-flay-auth-dev
  namespace: argocd
  annotations:
    # 1. Khai báo alias image cần theo dõi trong Helm Chart
    argocd-image-updater.argoproj.io/image-list: poly=registry.ftech.ai/southeast-asia-game/cambodia/flay-auth
    
    # 2. Định nghĩa chiến lược chọn tag mới nhất (dựa theo thời gian push lên Harbor)
    argocd-image-updater.argoproj.io/poly.update-strategy: latest
    
    # 3. Bộ lọc Regex chỉ chấp nhận tag chuẩn môi trường dev
    argocd-image-updater.argoproj.io/poly.allow-tags: regexp:^dev-[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}_[a-f0-9]+$
    
    # 4. Chỉ định phương thức ghi commit trực tiếp vào nhánh Git của repo Manifest
    argocd-image-updater.argoproj.io/write-back-method: git:secret:argocd/argocd-manifest-credential
    argocd-image-updater.argoproj.io/git-branch: main
```

---

## CHƯƠNG III: THIẾT KẾ PHÂN TẦNG HỆ THỐNG ARGOCD & QUẢN TRỊ DỰ ÁN

Hệ thống GitOps của FTech được tổ chức theo kiến trúc **Phân tầng hướng mô-đun (Hierarchical Modular GitOps)** chia làm 2 trục vận hành độc lập:

```
                                ┌────────────────────────────────────────────────────────┐
                                │               HỆ THỐNG GITOPS ARGOCD                   │
                                └────────────────────────────────────────────────────────┘
                [ TRỤC 1: QUẢN TRỊ ỨNG DỤNG & RBAC ]               [ TRỤC 2: HẠ TẦNG & BẢO MẬT CREDENTIALS ]
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

### 3.1. Trục 1: Quản trị Vòng đời Ứng dụng & Phân quyền (Application Stream)

Trục bên trái chịu trách nhiệm thiết lập ranh giới dự án, kiểm soát quyền truy cập của con người và quản lý vòng đời ứng dụng:

1. **`argocd-install` (Khởi tạo lõi ArgoCD):**
   * Triển khai bộ máy ArgoCD trên cụm K8s chính (Server, Repo Server, Application Controller, Redis Cache).
   * Tích hợp Single Sign-On (**Dex SSO**) liên kết trực tiếp với tài khoản GitLab nội bộ công ty (`@ftech.com.vn`), giúp nhân viên đăng nhập an toàn bằng tài khoản doanh nghiệp.
2. **`argocd-appprojects` (Thiết lập ranh giới dự án & Phân quyền RBAC):**
   * Định nghĩa thực thể `AppProject` để tạo vùng cô lập logic (**Logical Multi-tenancy**) cho từng dự án (`southeast-asia-game`, `webgl-game`, `fcloud`, `fedu`...).
   * **Source Repos Whitelist:** Chỉ định chính xác các Git repo được phép làm nguồn cấu hình, ngăn chặn việc trỏ tới repo không tin cậy.
   * **Destinations Whitelist:** Khóa chặt dự án chỉ được phép deploy vào đúng Cluster và Namespace được cấp phép (ví dụ: project `webgl-game` chỉ được phép deploy vào cluster `game` và namespace `webgl-game`).
   * **Cluster Resource Blacklist:** Chặn đứng việc tạo đè các tài nguyên nhạy cảm của cluster như `ClusterRole`, `ClusterRoleBinding`, `Namespace`.
   * **Casbin RBAC Policy:** Phân quyền chi tiết cho từng nhóm lập trình viên theo vai trò.
3. **`argocd-apps/app-of-apps` (Root Application):**
   * Khởi tạo **Root Application** cho từng dự án, quản lý việc quét tự động các ứng dụng con.
4. **`argocd-apps/{project}` (Child Applications):**
   * Chứa các file YAML định nghĩa từng dịch vụ/game độc lập, liên kết Helm Chart Manifest, cấu hình chính sách đồng bộ (`syncPolicy`) và tham số `argocd-image-updater`.

---

### 3.2. Trục 2: Quản trị Hạ tầng Nền tảng & Cấp phát Chứng thực (Infrastructure Stream)

Trục bên phải đảm bảo các thành phần nền tảng, chứng chỉ và kết nối bảo mật luôn sẵn sàng phục vụ các ứng dụng:

1. **`argocd-bootstrap-apps` (Infra Bootstrap Components):**
   * Quản lý tự động các công cụ hạ tầng nền tảng trên toàn bộ các cụm K8s:
     * **Ingress-Nginx & Cert-Manager:** Điều hướng lưu lượng mạng và tự động cấp phát chứng chỉ SSL/TLS.
     * **External Secrets Operator & Vault Agent Injector:** Cầu nối trích xuất dữ liệu nhạy cảm từ HashiCorp Vault.
     * **Prometheus, Grafana, Loki:** Bộ công cụ giám sát hiệu năng, log và cảnh báo.
2. **`argocd-manifest-credential` & `argocd-image-updater-regcreds`:**
   * Cung cấp Private Token an toàn (tích hợp đọc từ Vault) để ArgoCD và Image Updater có quyền đọc/ghi vào các Git Manifest Repo và truy vấn tag từ Harbor Container Registry.
3. **`argocd-apps/regcred` (Registry Credentials cấp phát tự động):**
   * Quản lý việc tạo Secret kéo Image (`dockerconfigjson`) vào **mọi Namespace trên tất cả các Cluster K8s**.
   * Sử dụng cơ chế `ApplicationSet` kết hợp `ExternalSecrets` để tự động kéo thông tin `robot$pull` từ Vault và đồng bộ thành Secret Kubernetes cục bộ.

---

### 3.3. Cơ chế tự động phát hiện ứng dụng (App-of-Apps & Recursive Discovery)

Để giải quyết bài toán mở rộng khi công ty có hàng trăm microservice và game mới ra mắt liên tục, hệ thống áp dụng cơ chế **Recursive App-of-Apps**:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-southeast-asia-game
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: southeast-asia-game
  source:
    repoURL: https://gitlab.ftech.ai/devops/gitops/argocd.git
    targetRevision: main
    path: argocd-apps/southeast-asia-game
    directory:
      recurse: true # Quét đệ quy toàn bộ thư mục con
  destination:
    name: in-cluster
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

* **Lợi ích vận hành:** Lập trình viên hoặc DevOps khi muốn đưa một service mới lên K8s **không cần truy cập Web UI ArgoCD để bấm tạo thủ công**. Chỉ cần commit một file YAML (ví dụ: `game-api-dev.yaml`) vào thư mục `argocd-apps/{project}/`, Root App sẽ tự động phát hiện trong vòng vài giây và kích hoạt ứng dụng đó lên cluster tương ứng.

---

### 3.4. Chiến lược Tách biệt Repository & Chuẩn hóa Manifest với Helm Chart Poly v3

Hệ thống tuân thủ nguyên tắc **Tách biệt mối quan tâm (Separation of Concerns)** bằng cách phân chia thành 2 loại Repository độc lập:

```
┌────────────────────────────────────────────────────────┐
│ 1. GitOps Orchestration Repository (argocd.git)       │
│ - argocd-appprojects/ : Quản lý RBAC, Whitelist Cluster│
│ - argocd-apps/        : Application YAML & Updater Annot│
│ ➔ Dành cho: Quản trị viên DevOps, DevSecOps            │
└────────────────────────────────────────────────────────┘
                           │
                           │ Trỏ tham chiếu
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Application Manifest Repository (manifest/{prj}.git)│
│ - values-dev.yaml     : Cấu hình CPU, RAM, Replicas Dev│
│ - values-prod.yaml    : Cấu hình CPU, RAM, Ingress Prod│
│ - Helm Library        : Sử dụng chung thư viện Poly v3 │
│ ➔ Dành cho: Developer & Application Team               │
└────────────────────────────────────────────────────────┘
```

#### Chuẩn hóa Thư viện Helm Chart Poly v3:
Toàn bộ các dự án microservice và game trong công ty không viết lại các file Kubernetes YAML thủ công (`Deployment.yaml`, `Service.yaml`, `Ingress.yaml`, `HPA.yaml`) mà sử dụng chung thư viện **Helm Chart Poly v3**.
* **Đặc điểm:** Thư viện này chuẩn hóa toàn bộ các mẫu cấu hình chuẩn doanh nghiệp: Graceful Shutdown, Readiness/Liveness Probes, Security Context, Ingress Annotations, và tự động inject `imagePullSecrets: [{name: "regcred"}]`.
* **Ưu điểm vượt trội:** Giảm kích thước file cấu hình từ hàng trăm dòng YAML phức tạp xuống còn một file `values-{env}.yaml` ngắn gọn (~20-30 dòng), loại bỏ hoàn toàn các lỗi sai sót cú pháp hoặc quên cấu hình giới hạn tài nguyên (Resource Limits).
* **Chuẩn hóa đặt tên:** Bắt buộc tuân thủ chuẩn RFC 1123 (`[a-z0-9-]`), cấm dùng ký tự gạch dưới `_` trong `metadata.name` và `helm.releaseName` để đảm bảo tương thích 100% với DNS nội bộ của Kubernetes.

---

## CHƯƠNG IV: QUẢN TRỊ BẢO MẬT & CHIẾN LƯỢC "ZERO-SECRET IN GIT"

Hệ thống kiên quyết thực hiện chiến lược **Zero-Secret in Git**: Không lưu trữ bất kỳ mật khẩu, khóa bí mật, API Token nào dưới dạng văn bản thô (Plain-text) trên Git repository.

### 4.1. Phân biệt bản chất 2 tầng Secret trong hệ thống

Một trong những điểm quan trọng nhất trong kiến trúc bảo mật của công ty là việc phân tách rõ ràng giữa **Secret kéo Image hạ tầng (`regcred`)** và **Secret ứng dụng runtime (`vault`)**:

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
| **Bản chất** | Kubernetes Secret kiểu `kubernetes.io/dockerconfigjson`. | Dữ liệu cấu hình ứng dụng (DB Password, Redis Auth, JWT Key...). |
| **Mục đích** | Cho Kubelet Node đăng nhập Harbor để **kéo Image container** về máy chủ. | Cho mã nguồn phần mềm bên trong Pod **kết nối Database, Third-party API**. |
| **Phạm vi quản lý** | Cấp độ toàn Namespace (**Namespace Scope**). | Cấp độ từng Pod / Microservice (**Pod Scope**). |
| **Vị trí định nghĩa** | Quản lý tập trung trong repo `manifest/regcred.git`. | Khai báo trong `values-*.yaml` của từng service backend cụ thể. |
| **Cơ chế nạp** | Tự động sinh qua **External Secrets Operator**. | Tự động inject qua **Vault Agent Injector (Sidecar)**. |
| **Đối tượng dùng** | **Tất cả các Pod** trong namespace (được Helm Poly v3 gán tự động). | **Chỉ các ứng dụng Backend/API** có nhu cầu kết nối DB/Bảo mật. |

---

### 4.2. Cơ chế cấp phát Image Pull Secret tự động qua External Secrets

1. DevOps lưu trữ tài khoản Robot Account của Harbor tại đường dẫn Vault: `secret/data/projects/{project}/regcred`.
2. Ứng dụng `ExternalSecret` định kỳ đối soát với Vault:
   * Trích xuất thông tin `auths.registry.ftech.ai` từ Vault.
   * Tạo ra 1 Kubernetes Secret có tên là `regcred` nằm sẵn trong namespace của dự án.
3. Khi Helm Chart Poly v3 triển khai bất kỳ ứng dụng nào vào namespace đó, Pod sẽ tự động đính kèm:
   ```yaml
   imagePullSecrets:
     - name: regcred
   ```
   Nhờ đó, Kubelet kéo được Image từ Harbor mà lập trình viên không cần can thiệp cấu hình secret kéo ảnh thủ công.

---

### 4.3. Cơ chế Inject Secret động cấp Pod qua HashiCorp Vault Agent Injector

Đối với các ứng dụng Backend/API, thông tin kết nối Cơ sở dữ liệu và API Key không bao giờ được đặt trong biến môi trường tĩnh (ConfigMap) trên Git. Thay vào đó, quy trình nạp secret diễn ra hoàn toàn động:

1. Trong file `values-{env}.yaml`, khai báo kích hoạt Vault:
   ```yaml
   poly:
     flay-auth:
       vault:
         enabled: true
         config:
           path: "secret/data/projects/southeast-asia-game/cambodia/flay-auth/dev"
           authPath: "auth/kubernetes-dev-new"
           role: "southeast-asia-game-flay-auth-dev-ro"
   ```
2. Khi Pod khởi tạo trên cụm K8s, **Vault Mutating Webhook** tự động gắn một container sidecar (`vault-agent`).
3. Sidecar xác thực với HashiCorp Vault thông qua **K8s ServiceAccount Token** của Pod.
4. Vault kiểm tra quyền (Policy), nếu hợp lệ sẽ trả về Secret. Sidecar ghi secret này vào một ổ đĩa bộ nhớ ảo (**ramfs memory** tại `/vault/secrets/config.env`).
5. Container chính của ứng dụng chỉ việc đọc file cấu hình này từ bộ nhớ RAM. Secret không bao giờ bị ghi xuống đĩa cứng hay lưu trữ thô trên Kubernetes etcd, đảm bảo tiêu chuẩn bảo mật ngân hàng/doanh nghiệp cao nhất.

---

### 4.4. Phân tích ca sử dụng thực tế: WebGL Static Game vs Backend Microservice

Trong quá trình rà soát hệ thống, có một trường hợp thực tế rất đáng lưu ý: **Tại sao các game WebGL (ví dụ: Game 108 `c108-jigsaw-anime-girl`) không có khối cấu hình `vault:` trong manifest?**

* **Giải thích kiến trúc:**
  1. **Game WebGL / HTML5 Canvas:** Là ứng dụng tĩnh chạy hoàn toàn phía Client (Trình duyệt web của người dùng) kết hợp cùng Web Server nhẹ (Nginx) để phục vụ file JS/CSS/HTML/Assets. Ứng dụng này **không kết nối Database nội bộ**, không chứa Private Key backend. Do đó, **không cần inject Secret runtime qua Vault**, giúp tiết kiệm tài nguyên CPU/RAM cho cluster vì không cần chạy sidecar container.
  2. **Backend Services (Auth, Payment, Game Server, API):** Bắt buộc phải cấu hình khối `vault:` để bảo vệ các thông tin nhạy cảm.

---

### 4.5. Mô hình Phân quyền Đa tầng & Kiểm soát Ranh giới qua Casbin RBAC Policy

ArgoCD quản trị quyền truy cập của các thành viên thông qua mô hình phân quyền **Casbin Policy Engine**:

```text
p, proj:<PROJECT_NAME>:<ROLE_NAME>, <RESOURCE>, <ACTION>, <OBJECT>, <EFFECT>
```

#### Ma trận Phân quyền Tiêu chuẩn của Công ty:

| Vai trò (Role) | Đối tượng áp dụng | Quyền hạn trên ArgoCD (`applications`) | Mục đích & Ranh giới bảo mật |
|---|---|---|---|
| **`read-only`** | QA, Tester, Junior Developer | `get` | Cho phép xem cây tài nguyên, xem log container, kiểm tra trạng thái pods. Không được phép can thiệp. |
| **`developer`** | Software Engineers | `get`, `sync`, `action/apps:Deployment:restart` | Cho phép chủ động Sync hoặc Restart Pod trên các môi trường thử nghiệm (**Dev / Staging**) để kiểm thử tính năng. |
| **`admin / lead`** | Tech Lead, DevOps Engineers | `get`, `create`, `update`, `delete`, `sync`, `override` | Toàn quyền kiểm soát và phê duyệt triển khai trên tất cả các môi trường, bao gồm cả môi trường **Production**. |

---

## CHƯƠNG V: ĐÁNH GIÁ HIỆU NĂNG, RỦI RO VẬN HÀNH & ĐỀ XUẤT TỐI ƯU HÓA

### 5.1. Bảng so sánh định lượng: CI/CD truyền thống vs Hệ thống GitOps hiện tại

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        BẢNG ĐÁNH GIÁ ĐỊNH LƯỢNG HỆ THỐNG                               │
├────────────────────────────┬────────────────────────────┬──────────────────────────────┤
│ TIÊU CHÍ SO SÁNH           │ MÔ HÌNH CI/CD TRUYỀN THỐNG │ HỆ THỐNG GITOPS HIỆN TẠI     │
├────────────────────────────┼────────────────────────────┼──────────────────────────────┤
│ 1. Kiểm soát phiên bản     │ Rời rạc, config nằm trên   │ Tập trung 100% trên Git      │
│    (Version Control)       │ nhiều pipeline CI          │ (Single Source of Truth)     │
├────────────────────────────┼────────────────────────────┼──────────────────────────────┤
│ 2. Quản trị Secret         │ Plain-text / Biến CI tĩnh  │ Zero-Secret, Vault động      │
│    (Secret Management)     │ ❌ Nguy cơ lộ lọt cao      │ 🔒 An toàn tuyệt đối         │
├────────────────────────────┼────────────────────────────┼──────────────────────────────┤
│ 3. Chống Configuration     │ Không có (Ai sửa K8s trực  │ Tự động phát hiện & ghi đè   │
│    Drift (Lệch cấu hình)   │ tiếp thì Git không biết)   │ phục hồi (Self-Healing)      │
├────────────────────────────┼────────────────────────────┼──────────────────────────────┤
│ 4. Tốc độ Rollback         │ Phải re-build hoặc re-run  │ < 1 phút (Chỉ cần revert     │
│    (Disaster Recovery)     │ lại pipeline CI cũ         │ commit trên Git)             │
├────────────────────────────┼────────────────────────────┼──────────────────────────────┤
│ 5. Chuẩn hóa hạ tầng       │ Mỗi team viết YAML một kiểu│ Thống nhất qua Helm Poly v3  │
│    (Standardization)       │ ❌ Dễ sai sót cú pháp      │ 🚀 Tái sử dụng tối đa        │
└────────────────────────────┴────────────────────────────┴──────────────────────────────┘
```

---

### 5.2. Nhận diện các điểm nghẽn và rủi ro tiềm ẩn trong vận hành

Mặc dù hệ thống đã hoạt động ổn định và hiện đại, qua quá trình nghiên cứu thực tế, chúng tôi ghi nhận một số điểm cần lưu ý:

1. **Độ trễ cập nhật Image khi mất Webhook (Polling Latency):**
   * Trong trường hợp mạng nội bộ gặp sự cố làm gián đoạn Webhook từ Harbor sang `argocd-image-updater`, hệ thống sẽ fallback về cơ chế quét định kỳ (Polling chu kỳ 2-3 phút). Điều này có thể khiến lập trình viên cảm giác việc deploy bị chậm.
2. **Quy trình Rollback khi bật cơ chế Auto-Image Updater:**
   * Nếu một phiên bản Image mới bị lỗi CrashLoopBackOff trong runtime, lập trình viên nhấn nút "Rollback" trên giao diện Web UI ArgoCD thì chỉ sau 1-2 phút, `argocd-image-updater` sẽ phát hiện tag mới trên Harbor và tự động commit ghi đè lại phiên bản lỗi.
   * **Quy trình chuẩn cần tuân thủ:** Bắt buộc phải thực hiện Rollback bằng cách `git revert` commit trên Git Manifest hoặc gắn nhãn chặn tag lỗi trên Harbor.
3. **Phụ thuộc vào tính sẵn sàng của HashiCorp Vault:**
   * Nếu cụm Vault bị niêm phong (Sealed) hoặc gặp sự cố mạng, các Pod mới khởi tạo sẽ không thể lấy được `regcred` (gây lỗi `ImagePullBackOff`) và không inject được runtime secret (gây lỗi `Init:Error`).

---

### 5.3. Đề xuất 3 sáng kiến nâng cấp hệ thống trong giai đoạn tiếp theo

Để đưa hệ thống GitOps của công ty đạt mức độ hoàn thiện cao nhất (**State-of-the-Art**), chúng tôi đề xuất lộ trình 3 bước tối ưu hóa:

```
                  ┌────────────────────────────────────────────────────────┐
                  │           LỘ TRÌNH 3 BƯỚC TỐI ƯU HÓA GITOPS            │
                  └────────────────────────────────────────────────────────┘
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      ▼                       ▼                       ▼
           ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
           │   BƯỚC 1: CANARY    │ │  BƯỚC 2: CHATOPS    │ │   BƯỚC 3: CI LINT   │
           │    DEPLOYMENT       │ │   NOTIFICATIONS     │ │   & OPA POLICY      │
           ├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤
           │ Tích hợp Argo       │ │ Tích hợp ArgoCD     │ │ Bổ sung Kubeconform │
           │ Rollouts phân luồng │ │ Notifications gửi   │ │ & Conftest chặn lỗi │
           │ traffic tự động &   │ │ cảnh báo Sync qua   │ │ cấu hình trước khi  │
           │ tự rollback theo 5xx│ │ Telegram/Slack/Teams│ │ merge vào Git.      │
           └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

#### 🚀 Sáng kiến 1: Triển khai Progressive Delivery với Argo Rollouts (Canary Deployment)
* **Hiện trạng:** Hệ thống đang sử dụng chiến lược Rolling Update mặc định của Kubernetes. Khi deploy phiên bản mới, nếu có lỗi logic bên trong code không làm sập Pod (nhưng trả về HTTP 500), hệ thống vẫn coi là thành công và thay thế toàn bộ pods cũ.
* **Giải pháp:** Tích hợp **Argo Rollouts** kết hợp với Prometheus Metrics.
  * Khi có bản mới, hệ thống chỉ phân luồng 10% traffic của người dùng thật vào Pod mới.
  * Tự động đo lường tỷ lệ lỗi (Error Rate) và độ trễ (Latency). Nếu tỷ lệ lỗi < 0.1%, tự động tăng dần lên 20% $\rightarrow$ 50% $\rightarrow$ 100%. Nếu tỷ lệ lỗi tăng vọt, hệ thống **tự động Rollback 100% về bản cũ trong vòng 5 giây** mà không cần con người can thiệp.

#### 🔔 Sáng kiến 2: Tự động hóa Thông báo Vận hành qua ChatOps (ArgoCD Notifications)
* **Giải pháp:** Cài đặt module `argocd-notifications` kết nối Webhook trực tiếp tới các kênh Telegram / Slack / Mattermost của từng dự án.
* **Nội dung thông báo:**
  * Thông báo ngay khi ứng dụng bắt đầu Sync, kèm theo tên dịch vụ, môi trường, Commit Message và Người thực hiện.
  * Gửi cảnh báo đỏ (Alert) kèm nguyên nhân chi tiết nếu Pod rơi vào trạng thái `Degraded`, `CrashLoopBackOff` hoặc `OutOfSync` kéo dài quá 5 phút.

#### 🛡️ Sáng kiến 3: Bổ sung Cổng Kiểm thử Cấu hình Tự động (CI Manifest Linting & OPA Policy)
* **Giải pháp:** Thiết lập pipeline CI tự động cho repo `manifest/{project}.git`:
  * Sử dụng **Kubeconform** để kiểm tra tính hợp lệ cú pháp của Schema Kubernetes.
  * Sử dụng **Conftest (Open Policy Agent - OPA)** để kiểm tra các chính sách an toàn: Bắt buộc phải có giới hạn CPU/RAM (Resource Limits), không được chạy container dưới quyền `root`, và kiểm tra Ingress Domain không được trùng lặp.
  * Nếu vi phạm, pipeline CI sẽ chặn không cho Merge Commit vào Git Manifest.

---

## KẾT LUẬN & KIẾN NGHỊ

Hệ thống GitOps trên nền tảng **ArgoCD + HashiCorp Vault + Helm Poly v3 + Kubernetes** hiện tại của công ty là một giải pháp kiến trúc xuất sắc, hiện đại và tuân thủ chặt chẽ các nguyên tắc bảo mật DevSecOps tiêu chuẩn quốc tế. 

Hệ thống đã giải quyết triệt để bài toán:
1. **Tự động hóa hoàn toàn luồng phân phối phần mềm từ Source Code đến Production.**
2. **Loại bỏ hoàn toàn rủi ro lộ lọt Secret trên Git và CI Runners.**
3. **Chuẩn hóa hạ tầng, giảm thiểu thời gian onboarding và chi phí vận hành cho các đội ngũ phát triển.**

**Kiến nghị Ban Giám đốc & Trưởng bộ phận:**
* Tiếp tục duy trì và nhân rộng mô hình GitOps chuẩn này cho 100% các dự án phần mềm, game và dịch vụ mới của công ty.
* Phê duyệt chủ trương triển khai thử nghiệm **Sáng kiến 1 (Argo Rollouts Canary Deployment)** và **Sáng kiến 2 (ChatOps Notifications)** trên môi trường Staging/Production trong Quý IV/2026 nhằm tiếp tục nâng cao độ ổn định và trải nghiệm vận hành cho toàn hệ thống.

---
*Báo cáo được lập và lưu trữ chính thức tại kho tài liệu kỹ thuật nội bộ.*
