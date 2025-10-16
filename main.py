import os, sys, json, datetime, pytz, requests, yaml, feedparser

KST = pytz.timezone("Asia/Seoul")

def kst_now():
    return datetime.datetime.now(KST)

def load_boot(path="orc_boot.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def fetch_rss_items(urls, limit=3):
    items = []
    for u in urls:
        try:
            d = feedparser.parse(u)
            for e in d.entries[:limit]:
                title = getattr(e, "title", "").strip()
                link = getattr(e, "link", "").strip()
                items.append(f"{title} — {link}")
        except Exception as ex:
            items.append(f"[RSS ERROR] {u}: {ex}")
    return items[:limit*len(urls)]

def fetch_crypto():
    # Coingecko 공개 API (키 불필요). 실패해도 보고는 계속.
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids":"bitcoin,ethereum","vs_currencies":"usd"},
                         timeout=10)
        j = r.json()
        btc = j.get("bitcoin",{}).get("usd")
        eth = j.get("ethereum",{}).get("usd")
        return btc, eth
    except Exception:
        return None, None

def daily_fortune(years):
    # MVP: 고정 포맷 (7/3) — 점수는 임시값
    out = []
    for y in years:
        out.append({
            "year": y,
            "total": 70, "money": 65, "love": 68, "health": 72,
            "advice": "속도보다 방향. 오늘은 점검/정리 우선.",
            "lucky_number": 7, "lucky_color": "네이비",
            "one_liner": "균형과 절제가 성과를 만든다."
        })
    return out

def make_report(cfg):
    today = kst_now().strftime("%Y-%m-%d (%a) KST")
    # ① FX/NBFI는 무료 요약 단계라 N/A 표기 (추후 보강)
    fx_line   = "USD/KRW: N/A, 3M KRW-USD basis: N/A, 외국인 주식/채권: N/A"
    nbfi_line = "NBFI 리스크 헤드라인/중앙은행 노트: N/A (무료 요약 단계)"
    # ③ 한국/일본 리테일 흐름 — 초기엔 “관측 중”으로 표기
    retail_line = "한·일 리테일 흐름: 해외 ETF/레버리지 관심 지속 (요약치 관측 중)"

    # ④ 기술센싱 RSS
    rss_urls = cfg.get("targets_metrics_methods",{}).get("tech",{}).get("targets",{}).get("rss",[])
    tech_items = fetch_rss_items(rss_urls, limit=3)

    # ⑤ 크립토
    btc, eth = fetch_crypto()
    crypto_line = (f"BTC: ${btc:,}, ETH: ${eth:,} (Coingecko)" 
                   if btc and eth else "크립토: N/A (API 제한/지연 가능)")

    # ⑥ 운세
    years = cfg["orc"]["fortune_birth_years"]
    fortunes = daily_fortune(years)
    f_lines = []
    for f in fortunes:
        f_lines.append(
          f"- {f['year']}년생 — 총운 {f['total']} / 재물 {f['money']} / 애정 {f['love']} / 건강 {f['health']}\n"
          f"  · 조언: {f['advice']} | 행운 숫자: {f['lucky_number']} | 색상: {f['lucky_color']}\n"
          f"  · 한 줄: {f['one_liner']}"
        )

    bullets = []
    bullets.append(f"{today} 아침 인텔 10–15줄 요약")
    bullets.append(f"① 환율·베이시스·외국인: {fx_line}")
    bullets.append(f"② NBFI 헤드라인/중앙은행: {nbfi_line}")
    bullets.append(f"③ 한국/일본 리테일: {retail_line}")
    bullets.append("④ 기술센싱 하이라이트:")
    for it in tech_items[:6]:
        bullets.append(f"   - {it}")
    bullets.append(f"⑤ 크립토: {crypto_line}")
    bullets.append("⑥ 운세(7/3) — 64·66·67·74")
    bullets.extend(f_lines)

    text = "\n".join(bullets)

    os.makedirs("./out", exist_ok=True)
    path = f"./out/daily_report.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    # 선택: 텔레그램 알림 (Secrets 설정 시)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": text[:4000]}
            )
        except Exception as ex:
            print("[WARN] Telegram send failed:", ex)

    # 상태 저장
    state = {"last_boot": kst_now().isoformat(), "report_path": path}
    with open("./out/save_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print("[OK] Report written:", path)

if __name__ == "__main__":
    cfg = load_boot()
    make_report(cfg)
