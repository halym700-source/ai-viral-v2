# RESH RANKS V3 — TAM OTOMATİK SHORTS (BAĞLANTI / TEST GEREKLİ)

**Durum:** Kod, n8n şablonu ve yerel 22.8 sn render testi hazır. Ancak YouTube otomatik indirmesi ve YouTube'a yayınlama henüz uçtan uca test edilmedi. n8n akışı güvenlik için inaktiftir. Kullanıcı tarafından yetkilendirilmiş hesap bağlantısı ve API anahtarı gerekir.

## Ne yapıyor?

1. Her gün Türkiye saatine göre **12.15 ve 19.15**'te n8n otomasyonu başlatır.
2. GitHub Actions'a yeni bir iş yollar.
3. GitHub Actions, YouTube Data API ile `videoLicense=creativeCommon` filtresiyle **tek temaya bağlı** kaynakları arar ve gerçek videoların `status.license` değerini tekrar doğrular.
4. İzlenme, konu uygunluğu, görüntü/ses varlığı ve geçmiş kullanılan kaynaklar üzerinden filtreler. Otomasyon erişilemeyen veya sessiz klipleri atlar; beş kullanılabilir kaynak bulamazsa **video yayınlamaz**.
5. İzni yeterli görülen videoların dosyalarını `yt-dlp` ile indirmeyi dener. YouTube bunu engellerse hiçbir erişim engeli aşılmaz ve görev hata verir.
6. FFmpeg ile **22.8 saniyelik** HPC (**Hook–Progression–Climax**) Shorts üretir: 1.6 sn merak uyandıran hook, 3.5 sn × 4 sıralama ve 7.2 sn final.
7. **1080×1920, 30 fps**, gerçek kaynak sesleri, ses yüksekliği dengeleme, #5–#1 numaraları, konu başlığı, @reshranks filigranı ve final ses patlaması için özel kurgu içerir.
8. MP4 ve içerik atıf manifestini GitHub Artifacts'a kaydeder. n8n çıktıyı indirir, süreyi / boyutu / kaynak sayısını kontrol eder.
9. n8n YouTube OAuth ile **ilk testte PRIVATE** olarak yükler ve gerçek YouTube bağlantısını kayıt eder.
10. Son 30 günlük GitHub kaynak manifestleriyle mümkün olduğunca aynı videoları tekrar seçmez.

## Bir kez yapılması gereken zorunlu kurulum (iPhone)

1. GitHub'da `halym700-source/ai-viral-v2` reposunu açın. **Settings → Secrets and variables → Actions → New repository secret** yolunda `YOUTUBE_DATA_API_KEY` adlı gizli anahtar ekleyin. Anahtarı sohbet üzerinden göndermeyin. Bu anahtar Google Cloud'da YouTube Data API v3 etkinleştirilerek oluşturulur ve yalnızca YouTube Data API ile kısıtlanması önerilir.
2. **GitHub Actions** bölümünde `ReshRanks HPC Autopilot` iş akışının yer aldığını doğrulayın.
3. iPhone'da `https://halym700.app.n8n.cloud` adresinde **Workflows → Import from File** kullanarak `workflows/RESH_RANKS_V3_FULL_AUTOPILOT_N8N.json` dosyasını içe aktarın.
4. n8n içindeki **03, 05, 10 ve 13** numaralı GitHub HTTP Request düğümlerinin `Header Auth` kimlik bilgilerini seçin. Mevcut başka otomasyondaki GitHub credential uygun izne sahipse tekrar kullanılabilir. Token'ı düğümün koduna yazmayın.
5. **17 YouTube OAuth - PRIVATE TEST ONLY** düğümüne mutlaka **ReshRanks** YouTube kanalının hesabını bağlayın. Önceden kullanılan `YouTube Account 3` başka kanala aitse **kullanmayın**. Yanlış kanalın yetkilendirilmesi yanlış kanala yayın yapılmasına neden olur.
6. İlk testte yayın gizliliği zaten `private` olarak ayarlanmıştır. Video doğru kanala, doğru başlık ve kaynak atfıyla yüklendikten sonra `public` ayarına alın.
7. Akışı **Execute Workflow** ile test edin. Hata varsa GitHub Actions loglarını kontrol edin. Başarılı uçtan uca testten sonra workflow'u **Active** yapın.
8. n8n zaman dilimini `Europe/Istanbul` olarak kontrol edin. **Günde iki video**; kaynak bulamazsa yayın yok.

## Çalışma sınırları

- Videolarda **YouTube'un Creative Commons lisans etiketi**, bütün görüntü/ses unsurlarının haklarının kesin olarak temiz olduğunu garanti etmez. İzinli kaynaklara ve özgün dönüştürücü kurguya öncelik verilmeli; YouTube yeniden kullanılan içerik ve telif kuralları her zaman geçerli.
- `yt-dlp` YouTube'daki her videoyu otomatik olarak indiremez; platform engellerini atlatacak oturum bilgisi/kilit aşma kullanılmaz.
- Başlık/kurgu optimizasyonu bir büyüme deneyidir; otomatik viral olma veya para kazanma garantisi vermez.
- `YouTube Account 3` ReshRanks değilse yanlış kanal yüklemesi riski vardır; ilk testte hesap mutlaka kontrol edilmelidir.
- ChatGPT Plus aboneliği n8n/GitHub Actions çalışmasını tek başına sürdürmez veya durdurmaz. Bağımsız servislerin ücretsiz/ücretli plan limitleri geçerlidir.
- **YouTube API anahtarı ve OAuth bağlantısı verilmeden otomasyon aktif değildir.**
- Video indirme işlemi geçersiz olursa hiçbir video yayınlanmaz; hata n8n geçmişinde yer alır.

## GitHub'daki dosyalar

- `.github/workflows/reshranks_autopilot.yml`
- `reshranks_autopilot/discover.py`
- `reshranks_autopilot/render.py`
- `workflows/RESH_RANKS_V3_FULL_AUTOPILOT_N8N.json`
- `RESH_RANKS_V3_KURULUM_TR.md`
## Gercek GitHub Actions test sonucu (2026-10-31)

- Test 1: `YOUTUBE_DATA_API_KEY` eksik (GitHub run 41161875800).
- Test 2: Mevcut `YOUTUBE_RESEARCH_API_KEY` anahtariyla CC YouTube aramasi calisti: 34 aday bulundu (run 41161923706).
- Test 2: Uc bagimsiz Youtube videosu `yt-dlp` ile indirilemedi; YouTube otomatik erisim icin oturum dogrulamasi istedi. Basarili download: 0/3.
- GitHub V3 workflow'unda `YOUTUBE_DATA_API_KEY || YOUTUBE_RESEARCH_API_KEY` yedegi eklendi; artik yeni API anahtari olusturulmadan arama calisabilir.
- Bulunan dosyalarla H264/AAC 1080x1920, 22.82 sn yerel render testi basariliydi. Bu, otomatik Youtube indirme basarisi anlamina gelmez.
- **Canli otomatik indir/yayin sistemi aktif DEGIL**. n8n OAuth kurulumu ve indirme icin izinli/guvenilir erisim cozumu gerekiyor. YouTube oturum veya bot engeli asilmasi saglanmiyor.
- Butun testler YouTube'a video yuklemeden calistirildi.


## 2026-10-31: Otomatik indirme icin test edilmis yedek yontem

- Duz YouTube download testinde tv/web_safari, Android, iOS ve web_embedded oynatici istemcilerinin **tamami oturum/bot dogrulamasi nedeniyle basarisiz** oldu. Test: https://github.com/halym700-source/ai-viral-v2/actions/runs/41162343164
- Wikimedia Commons uzerinde orijinal YouTube video kimligi ile **otomatik arama basarili**: `R-YJw6-Sshk` kimligi Wikimedia'daki dogru arsiv dosyasiyla eslesti.
- Commons dosyasinda **CC BY 3.0** lisans bilgisi kontrol edildi; 12,978,534 bayt video indirildi, FFprobe ile goruntu ve orijinal ses kanallari dogrulandi. Test: https://github.com/halym700-source/ai-viral-v2/actions/runs/41162786336
- V3 arama motoruna `reshranks_autopilot/commons_mirror.py` dosyasi ve **yalnizca birebir YouTube video ID'si ve CC-BY lisansi eslesen** Wikimedia Commons arsiv kopyasini indirmeyi deneyen yedek yol eklendi. Bu yol Youtubedaki tum videolar icin bulunmayabilir.
- Kaynak bulunamazsa veya orijinal ses yoksa hicbir yanlis kaynak kullanilmaz ve yayin baslatilmaz.
- CC BY arsiv kaynagi kullanilirsa olusan YouTube aciklamasina arsi̇v ve lisans URL'leri dahil edilir.
- Baska bir testte Pixabay'dan dogrudan MP4 indirildi (1,847,363 bayt), **ama video ses kanali icermiyordu**; motor sesleri rankinginde bu kaynak uygun kabul edilmez. Test: https://github.com/halym700-source/ai-viral-v2/actions/runs/41162413001
- Tum denemeler YouTube'a video yuklemeden yapildi. n8n OAuth baglantisi ve 5 kullanilabilir eslesmenin canli testi tamamlanmadigi icin tum surecin otomatik yayina hazir oldugu iddia edilmez.
