# Kesit Studio — Free OpusClip-style pipeline

Bu özellik mevcut repository'ye ayrı bir workflow olarak eklendi ve mevcut workflow'lara dokunmaz.

## Akış

YouTube / canlı yayın kaydı URL'si -> yt-dlp -> YouTube altyazısı varsa onu kullan -> yoksa yerel faster-whisper -> otomatik önemli an skoru -> 25-60 sn kesitler -> 9:16 1080x1920 -> gömülü Türkçe/algılanan dil altyazı -> MP4 + SRT + SEO metadata -> ZIP.

Claude API, OpenAI API veya başka ücretli API kullanılmaz.

## Yeni özellik

YouTube'da altyazı bulunmayan videolarda sistem artık **yerel Whisper** ile konuşmayı çözümler. Böylece sadece altyazısı olan videolara bağımlı değildir.

Varsayılan Whisper modeli: `base`.
Daha hızlı çalışması için `WHISPER_MODEL=tiny`, daha iyi doğruluk için `WHISPER_MODEL=small` kullanılabilir.

## Kullanım

GitHub'da **Actions -> Kesit Studio - Free YouTube Clips -> Run workflow** bölümünden YouTube URL'sini girip çalıştır.

Canlı yayın için yayın bittikten sonra oluşan YouTube tekrar/VOD bağlantısını vermek en güvenilir yöntemdir. Çok uzun yayınlar GitHub runner süresi ve kaynakları nedeniyle daha uzun sürebilir.

## Ücretsiz sürümün sınırı

GitHub-hosted runner süre ve kullanım limitlerine tabidir. Bu nedenle sınırsız ücretsiz video işleme garantisi yoktur.

## Önemli

Bu sürüm otomatik kesit seçimini yerel metin/konuşma sinyalleriyle yapar; ücretli bir LLM kullanmaz. Bu nedenle OpusClip'in ticari AI sıralaması kadar bağlamsal olmayabilir, fakat API ücreti ve filigran gerektirmez.
