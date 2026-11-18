# Kesit Studio — Free GitHub Actions

Bu özellik mevcut repository'ye ayrı bir workflow olarak eklendi ve mevcut workflow'lara dokunmaz.

## Akış

YouTube URL -> yt-dlp -> Türkçe/İngilizce altyazı -> yerel skor algoritması -> kısa kesitler -> 9:16 1080x1920 -> gömülü altyazı -> MP4 + SRT + SEO metadata -> ZIP.

Claude API, OpenAI API veya başka ücretli API kullanılmaz.

## Kullanım

GitHub'da **Actions -> Kesit Studio - Free YouTube Clips -> Run workflow** bölümünden YouTube URL'sini girip çalıştır.

## Ücretsiz sürümün sınırı

Video üzerinde erişilebilir Türkçe veya İngilizce altyazı bulunması gerekir. Altyazı yoksa sistem ücretli bir API'ye geçmez; işi hata ile durdurur.

GitHub-hosted runner süre ve kullanım limitlerine tabidir. Bu nedenle sınırsız ücretsiz video işleme garantisi yoktur.
