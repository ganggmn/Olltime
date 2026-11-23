# 올타임 (Vercel 배포용)

올림픽공원 지금 혼잡도와 공연 날 언제 가고 언제 나오면 덜 붐비는지 알려주는 사이트예요.

## 폴더 구성

| 파일 | 하는 일 |
|---|---|
| index.html | 사이트 화면 전체 (공연 일정, 작년 주차 기록, 지하철 노선도는 안에 들어 있어요) |
| api/now.js | 서울시 실시간 도시데이터(올림픽공원)를 받아 작게 줄여 줘요. 5분 동안 저장해서 서울시는 5분에 한 번쯤만 불러요 |
| api/parking.js | 올림픽공원 실시간 주차 대수(동2, 남2, 북2문 합계). 10분 동안 저장 |
| api/_city.js | 서울시 응답을 줄이는 코드 (주소로 열리지 않아요) |
| privacy.html, terms.html | 개인정보 처리방침, 이용약관 |
| vercel.json | 주소 정리, 보안 헤더 |

서울시 데이터를 못 받으면 화면에 "잠시 불러오지 못했어요"라고 띄우고, 공연 예상과 플래너는 그대로 보여줘요.

## 배포 (처음 한 번)

1. GitHub에서 새 저장소를 **Private**으로 만들어요. 이름 예: `olltime`
2. 이 `olltime-web` 폴더 **안의 파일들만** 저장소에 올려요. (공모전 폴더의 `.env`, `data` 폴더는 절대 올리지 않아요)
3. vercel.com → Add New → Project → 방금 만든 저장소 Import → 설정은 그대로 두고 Deploy
4. 프로젝트 Settings → Environment Variables
   - Key: `SEOUL_KEY`
   - Value: 서울 열린데이터광장 일반 인증키 (맥북 `.env`의 SEOUL_KEY와 같은 값)
   - **Sensitive** 켜기, Production과 Preview 체크
5. Deployments → 맨 위 배포 → Redeploy (환경변수는 다시 배포해야 적용돼요)
6. 확인: `https://주소.vercel.app/api/now` 를 열어서 `"now":{"time":...` 가 나오면 성공이에요. 키는 화면에 나오지 않아요.

## 배포 뒤 할 일

- privacy.html, terms.html 의 `[운영자 이름]`, `[연락 이메일]` 을 채워요.
- 서울 열린데이터광장 활용갤러리에 사이트 주소를 등록하면 실시간 지하철 API 호출 한도가 풀려요(나중에 사이트에 지하철 도착 정보를 붙일 때).

## 고칠 때

index.html은 `src/`의 조각을 합쳐 만들어요. `src/head.html`(CSS), `src/body.html`(본문), `src/app.js`(동작), `src/data/`(공연, 지도, 노선, 정확도 숫자)를 고친 뒤 `python3 src/assemble.py`를 돌리면 index.html이 다시 만들어져요. `src/`는 `.vercelignore`로 배포에서 빠져요.

정확도 숫자(`src/data/accuracy.json`)는 맥의 `analyze_accuracy.py`가 모아 둔 서울시 데이터로 계산해요. 다시 돌리면 날이 쌓인 만큼 새로 계산돼요.
