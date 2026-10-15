# Thầy đang yêu cầu Dũng và Hiếu làm gì?

Đây là bản diễn giải dễ thực hiện từ phản hồi của thầy. Mục tiêu trước mắt
không phải là thêm model, thêm prompt hay tìm F1 cao hơn. Mục tiêu là chứng
minh rằng số liệu hiện tại đáng tin, model có tín hiệu phân biệt thật, và biết
chính xác thành phần nào tạo ra tác dụng.

## Điều thầy muốn hai bạn hiểu trước tiên

Các kết quả hiện tại chưa cho thấy mô hình phân biệt vulnerable và safe tốt.
MCC của các cấu hình rất thấp; nhiều trường hợp F1/Recall tăng vì model đoán
`vulnerable` nhiều hơn, không phải vì đọc code tốt hơn. Trên Devign, baseline
luôn đoán vulnerable đã có F1 rất cao; trên Reveal, baseline luôn đoán safe có
Accuracy cao do dữ liệu lệch lớp.

Vì vậy, từ bây giờ không được kết luận chỉ vì F1 hoặc Accuracy tăng. Muốn nói
"cải tiến tốt hơn" phải nhìn cùng lúc:

- confusion matrix: TP, TN, FP, FN;
- MCC và balanced accuracy;
- tỷ lệ model đoán vulnerable;
- baseline luôn-vulnerable và luôn-safe trên đúng cùng ID;
- coverage/invalid rate nếu LLM không trả lời đúng format;
- confidence interval ghép cặp khi so sánh hai phương pháp trên cùng mẫu.

Nếu MCC vẫn quanh 0 sau khi đã kiểm tra kỹ, kết quả đúng không phải là tiếp tục
thêm component. Khi đó phải chuyển sang giải thích failure mode: parser sai,
nhãn nhiễu, graph không vào prompt, context bị cắt, demo không liên quan,
leakage/trùng code, hoặc model chỉ bắt chước nhãn demo.

## Việc chung bắt buộc cho cả hai

### 1. Làm sạch parser và phản hồi LLM

- Kiểm tra mọi parser đang dùng.
- Có test cho `0`, `1`, `Vulnerable`, `Non-vulnerable`, response rỗng và
  response sai format.
- `Non-vulnerable` tuyệt đối không được bị parse thành `1` vì chứa từ
  `vulnerable`.
- Response không parse được phải là `invalid`, không tự đổi thành `0`.
- Re-parse raw response đã lưu, không gọi LLM lại.
- Báo cáo: bao nhiêu nhãn đổi, đổi ở lớp nào, parse method nào, bao nhiêu ca
  invalid và metric trước/sau.
- Chốt trước retry policy. Hết retry vẫn là invalid và vẫn phải tính vào báo
  cáo coverage; không âm thầm bỏ khỏi mẫu số.

### 2. Dùng một evaluator chung

Mọi run phải đi qua cùng một script đánh giá. Script đó đọc prediction theo
từng ID và tính đủ metric/baseline nêu trên. Không để mỗi notebook tự tính một
bộ số khác nhau.

Với so sánh chính giữa A và B:

- dùng cùng target IDs;
- bootstrap ghép cặp cho chênh lệch MCC/F1;
- McNemar dựa trên A đúng/B sai và A sai/B đúng;
- nếu CI chứa 0 thì ghi "chưa đủ bằng chứng về lợi ích", không nói hai bên
  tương đương.

### 3. Lập run ledger

Mỗi dòng run cần có ít nhất:

- run ID và Git commit;
- model, provider, temperature, max tokens, seed;
- dataset, split, danh sách target IDs và số mẫu mỗi lớp;
- retrieval pool/candidate IDs/demo IDs;
- prompt hash, token count và nội dung bị cắt;
- đường dẫn raw response, prediction, parser report, metric report;
- chi phí/thời gian nếu có;
- ghi rõ test label đã từng được dùng để chọn cấu hình hay chưa.

Nếu artifact cũ không còn thông tin, ghi `không truy xuất được`; không tự suy
diễn lại.

### 4. Chưa so sánh trực tiếp hai bạn nếu điều kiện khác nhau

Dũng và Hiếu đang dùng backbone/split/retrieval pool có thể khác nhau. Vì vậy
chưa được kết luận hướng nào tốt hơn dựa vào bảng hiện tại.

Muốn so sánh trực tiếp phải cố định cùng:

- LLM;
- target IDs;
- retrieval pool;
- inference parameters;
- context/truncation policy;
- prompt/evaluator.

### 5. Kiểm tra rò rỉ và tính độc lập dữ liệu

- Target label chỉ dùng lúc evaluation; không được đi vào retrieval, pair
  selector hay prompt renderer.
- Kiểm tra duplicate ID, duplicate code và near-duplicate giữa retrieval pool
  với target.
- Checkpoint phải mang hash dataset/split/model/prompt/retrieval. Không khớp
  thì không được resume.
- Khi chạy subset để tiết kiệm, chỉ giảm số target gọi LLM; retrieval pool vẫn
  là full train pool.

## Việc Dũng cần làm

### A. Đối soát V1/V2 trước khi nói về cải tiến

- Gửi/giữ prediction theo từng ID, raw response và prompt thực đã gửi.
- Rà lại parser trong pipeline Dũng và re-parse mọi response còn lưu được.
- Với CSV cũ không có ID/raw response: chỉ gọi là historical/archival result;
  không dùng để paired bootstrap, McNemar hoặc kết luận component nào tốt hơn.
- Lập bảng "bài GRACE - code tác giả - code Dũng" cho embedding, retrieval,
  syntax similarity, graph, số demo, prompt order và truncation. Khác đâu ghi
  rõ khác đó; không gọi là reproduce exact nếu chỉ là approximation.

### B. Kiểm tra graph thật sự đi vào model

- Mở prompt thực, không chỉ đọc code tạo prompt.
- Báo graph coverage, graph export success/failure, số node/edge và phần graph
  bị cắt.
- Nếu graph rỗng hoặc export lỗi thì không được gọi run đó là graph-grounded.
- Khi test tác dụng graph: giữ code, demo, nhãn demo, instruction và retrieval
  cố định; chỉ bỏ graph khỏi prompt. Không retrieve lại demo.

### C. Tách từng giả thuyết V2

Không chạy tất cả C5-C8 rồi gán kết quả cho từng component.

- Test graph verbalization: cùng node/edge, chỉ đổi cách diễn đạt.
- Test graph slicing: cùng cách diễn đạt, chỉ đổi slice.
- Test MMR: cùng số demo và cùng điều kiện nhãn, chỉ đổi rule chọn demo.
- Không vừa tăng 2 lên 4 demo vừa bật MMR rồi nói đó là lợi ích MMR.

### D. Hiểu đúng kết quả cũ

- Recall/F1 cao nhưng MCC thấp nghĩa là có thể model đang đoán vulnerable quá
  nhiều.
- GEPA phải ghi objective, dev set dùng tối ưu và prompt cuối. Nếu tiếp tục,
  thử objective MCC/balanced accuracy nhưng vẫn phải test trên dữ liệu chưa
  dùng để chọn prompt.
- Artifact Devign staged đã audit có graph rỗng thì không dùng để chứng minh
  GraphVerb hiệu quả.

## Việc Hiếu cần làm

### A. Parser, checkpoint và mock mode

- Sửa parser `Non-vulnerable` nếu có lỗi match `vulnerable` trước.
- Không default response lỗi thành safe.
- Thiếu API key/model/data phải fail rõ ràng, không tự chuyển sang mock.
- Checkpoint phải gắn hash toàn bộ config; không resume nhầm run khác.

### B. Đánh giá lại security-aware retrieval

Điểm `Security Relevance` hiện không đủ để chứng minh reranker tốt hơn nếu
reranker cũng tối ưu chính security similarity đó. Đây là tự chấm bằng thước
mình vừa tối ưu.

Hiếu cần:

- thêm random-demo baseline từ đúng retrieval pool;
- thống kê bao nhiêu signature rỗng;
- kiểm tra quy ước hai set rỗng có bị xem là giống nhau hoàn toàn hay không;
- báo đóng góp từng feature vào security score;
- không diễn giải Label Agreement hoặc same-label demo như bằng chứng cơ chế
  lỗ hổng;
- không gọi `dangerous demo` là nguyên nhân model sai nếu chưa có đối chứng
  cùng target, giữ nguyên mọi thứ khác, chỉ thay demo.

### C. Làm security signature bớt bề mặt

Có `memcpy`, `NULL`, `[]`, `->` hay một phép so sánh không tự chứng minh hai
hàm cùng security mechanism. Cần kiểm tra:

- sink nào đang nguy hiểm;
- biến nào đi vào sink;
- guard kiểm tra có đúng biến đó không;
- guard có xảy ra trước sink không;
- còn nhánh nào đi tới sink mà không qua guard không.

Không cần xây full static data-flow analyzer ngay. Nhưng phải tạo micro-example
có đáp án rõ: guard đúng biến, guard sai biến, guard sau sink, và guard chỉ che
một nhánh. Heuristic nào không chứng minh được đường nối source-sink thì phải
gọi đúng là heuristic clue.

### D. Kiểm tra contrastive selector và prompt

- Thống kê fallback khi top-50 thiếu một nhãn: tần suất, thiếu nhãn nào, demo
  nào bị lấy bổ sung, cuối cùng demo nào được chọn.
- Không dùng 5 mẫu đầu train không liên quan target làm fallback mà không ghi
  nhận.
- Kiểm tra `security_critical_difference` có thật sự đi vào prompt không.
  Nếu chưa, không được viết như thể model đã nhìn thấy nó.
- Đảo thứ tự vulnerable/safe demo.
- Làm demo-label-flip control: giữ code/demo/order, chỉ đảo nhãn hiển thị và
  đo prediction đổi bao nhiêu; chạy lặp prompt không đảo nhãn để tách dao động
  tự nhiên của LLM.

## Chấm retrieval thủ công: hai bạn cùng làm

Ở dev set, lấy 50 target Devign và 50 target Reveal có cả hai nhãn. Với từng
target, lấy demo của hai retriever, che tên phương pháp/score, tráo thứ tự rồi
chấm độc lập.

Mỗi cặp target-demo cần ghi:

- thao tác nhạy cảm/sink;
- biến liên quan;
- guard;
- guard liên quan gì tới sink;
- dòng code làm bằng chứng;
- hoặc `chưa xác định`.

Giữ lại ca bất đồng trước khi hai bạn trao đổi. Cùng CWE hoặc cùng nhãn chỉ là
tín hiệu phụ, không thay thế đánh giá bằng chứng trong code. RAGAS chưa phù
hợp với output nhị phân 0/1, nên bỏ khỏi đợt hiện tại.

## Thứ tự làm việc thầy muốn

### Đợt 1 — đối soát nền

Làm parser, evaluator, run ledger, split/ID audit, raw artifact audit,
checkpoint và kiểm tra graph/retrieval thật sự. Chưa chạy phương pháp mới,
chưa cần benchmark lớn.

### Đợt 2 — chỉ kiểm tra một giả thuyết

Ví dụ: security-aware reranking có lợi không khi candidate pool, số demo,
prompt, model và token budget đều giống nhau?

Chạy đúng ablation cần thiết, label-flip/order control, manual review và
leakage audit. Nếu có tiền, lặp lại trên model mạnh hơn nhưng điều kiện vẫn
phải giữ cố định.

### Đợt 3 — xác nhận và giải thích

Chỉ khi Đợt 2 có tín hiệu đáng tin: mở rộng số mẫu, chạy nhiều seed, tính CI,
phân tích lỗi, báo chi phí và kiểm tra external data. Nếu giả thuyết thất bại,
báo cáo failure mode là kết quả nghiên cứu hợp lệ.

## Definition of done cho một kết luận "cải tiến có tác dụng"

Chỉ được nói một cải tiến có tác dụng khi:

1. Parser, ID, split, raw response và prompt đều truy vết được.
2. Ablation chỉ thay đúng component đang xét.
3. MCC/balanced accuracy cải thiện trên development đã đăng ký trước.
4. Paired 95% CI cho chênh lệch chính không chứa 0.
5. Không thắng chỉ nhờ dự đoán một lớp nhiều hơn.
6. Retrieval/demonstration đã qua kiểm tra độc lập hoặc chấm mù.
7. Cấu hình được đóng băng trước test/external evaluation.
