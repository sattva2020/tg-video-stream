//! Аудио и видео фильтры FFmpeg
//!
//! Генерация строк фильтров для FFmpeg -vf (видео) и -af (аудио) опции.

use crate::models::EqPreset;

// ==================== ВИДЕО ФИЛЬТРЫ ====================

/// Генерирует transpose фильтр для коррекции ориентации видео
///
/// # Arguments
/// * `orientation` - угол поворота в градусах (0, 90, 180, 270)
///
/// # Returns
/// Строка с transpose фильтром или пустая строка для orientation=0
///
/// # Examples
/// ```
/// assert_eq!(transpose_filter(90), "transpose=2");
/// assert_eq!(transpose_filter(180), "transpose=1,transpose=1");
/// assert_eq!(transpose_filter(270), "transpose=1");
/// assert_eq!(transpose_filter(0), "");
/// ```
pub fn transpose_filter(orientation: u32) -> String {
    match orientation {
        90 => "transpose=2".to_string(),      // 90° counter-clockwise
        180 => "transpose=1,transpose=1".to_string(), // 180° (два раза 90° CW)
        270 => "transpose=1".to_string(),     // 90° clockwise (270° CCW)
        0 => String::new(),                   // Без изменений
        _ => String::new(),                   // Некорректное значение - игнорируем
    }
}

/// Генерирует scale фильтр для изменения разрешения
///
/// # Arguments
/// * `width` - ширина в пикселях (None = auto)
/// * `height` - высота в пикселях (None = auto)
///
/// # Returns
/// Строка scale фильтра или пустая строка если оба None
///
/// # Examples
/// ```
/// assert_eq!(scale_filter(Some(1920), Some(1080)), "scale=1920:1080");
/// assert_eq!(scale_filter(None, Some(720)), "scale=-2:720");
/// assert_eq!(scale_filter(Some(1280), None), "scale=1280:-2");
/// assert_eq!(scale_filter(None, None), "");
/// ```
pub fn scale_filter(width: Option<u32>, height: Option<u32>) -> String {
    match (width, height) {
        (Some(w), Some(h)) => format!("scale={}:{}", w, h),
        (Some(w), None) => format!("scale={}:-2", w),
        (None, Some(h)) => format!("scale=-2:{}", h),
        (None, None) => String::new(),
    }
}

/// Генерирует fps фильтр для изменения частоты кадров
///
/// # Arguments
/// * `fps` - целевой FPS
///
/// # Returns
/// Строка fps фильтра
pub fn fps_filter(fps: u32) -> String {
    format!("fps={}", fps)
}

/// Объединяет видео фильтры в цепочку
///
/// # Arguments
/// * `filters` - список строк видео фильтров
///
/// # Returns
/// Объединённая строка фильтров через запятую (пустые фильтры пропускаются)
pub fn chain_video_filters(filters: &[String]) -> String {
    filters
        .iter()
        .filter(|f| !f.is_empty())
        .cloned()
        .collect::<Vec<_>>()
        .join(",")
}

/// Строит полную цепочку видео фильтров
///
/// # Arguments
/// * `orientation` - опциональная ориентация (0, 90, 180, 270)
/// * `width` - опциональная ширина для масштабирования
/// * `height` - опциональная высота для масштабирования
/// * `fps` - опциональный FPS
///
/// # Returns
/// Полная цепочка FFmpeg video filters (-vf) или пустая строка
pub fn build_video_filter_chain(
    orientation: Option<u32>,
    width: Option<u32>,
    height: Option<u32>,
    fps: Option<u32>,
) -> String {
    let mut filters = Vec::new();

    // 1. Orientation correction (прежде всего)
    if let Some(o) = orientation {
        if o != 0 {
            filters.push(transpose_filter(o));
        }
    }

    // 2. Scale (разрешение)
    let scale = scale_filter(width, height);
    if !scale.is_empty() {
        filters.push(scale);
    }

    // 3. FPS (последним)
    if let Some(f) = fps {
        filters.push(fps_filter(f));
    }

    chain_video_filters(&filters)
}

// ==================== АУДИО ФИЛЬТРЫ ====================

/// Генерирует фильтр fade in
///
/// # Arguments
/// * `duration` - длительность fade in в секундах
pub fn fade_in(duration: f32) -> String {
    format!("afade=t=in:st=0:d={:.2}", duration)
}

/// Генерирует фильтр fade out
///
/// # Arguments
/// * `start` - время начала fade out в секундах
/// * `duration` - длительность fade out в секундах
pub fn fade_out(start: f32, duration: f32) -> String {
    format!("afade=t=out:st={:.2}:d={:.2}", start, duration)
}

/// Генерирует фильтр loudnorm для нормализации громкости
///
/// # Arguments
/// * `target_lufs` - целевой уровень в LUFS (обычно -16 или -14)
pub fn loudnorm(target_lufs: f32) -> String {
    format!(
        "loudnorm=I={:.1}:TP=-1.5:LRA=11:print_format=none",
        target_lufs
    )
}

/// Генерирует фильтр volume для изменения громкости
///
/// # Arguments
/// * `db` - изменение в децибелах (положительное = громче)
pub fn volume(db: f32) -> String {
    format!("volume={:.1}dB", db)
}

/// Генерирует фильтр highpass для удаления низких частот
///
/// # Arguments
/// * `frequency` - частота среза в Hz
pub fn highpass(frequency: u32) -> String {
    format!("highpass=f={}", frequency)
}

/// Генерирует фильтр lowpass для удаления высоких частот
///
/// # Arguments
/// * `frequency` - частота среза в Hz
pub fn lowpass(frequency: u32) -> String {
    format!("lowpass=f={}", frequency)
}

/// Генерирует equalizer фильтр
///
/// # Arguments
/// * `frequency` - центральная частота в Hz
/// * `width_type` - тип ширины полосы ('q', 'h', 'o', 's')
/// * `width` - значение ширины
/// * `gain` - усиление в dB
pub fn equalizer(frequency: u32, width_type: char, width: f32, gain: f32) -> String {
    format!(
        "equalizer=f={}:width_type={}:width={:.2}:g={:.1}",
        frequency, width_type, width, gain
    )
}

/// Генерирует фильтр compand (компрессор/экспандер)
///
/// # Arguments
/// * `attack` - время атаки в секундах
/// * `decay` - время затухания в секундах
pub fn compressor(attack: f32, decay: f32) -> String {
    format!(
        "compand=attacks={:.3}:decays={:.3}:points=-80/-80|-12/-12|0/-6|20/-6",
        attack, decay
    )
}

/// Генерирует фильтр aresample для ресемплинга
///
/// # Arguments
/// * `sample_rate` - целевой sample rate
pub fn resample(sample_rate: u32) -> String {
    format!("aresample={}", sample_rate)
}

/// Генерирует фильтр pan для изменения каналов
///
/// # Arguments
/// * `channels` - количество выходных каналов (1=mono, 2=stereo)
pub fn channels(count: u8) -> String {
    match count {
        1 => "pan=mono|c0=0.5*c0+0.5*c1".to_string(),
        2 => "pan=stereo|FL=FL|FR=FR".to_string(),
        _ => format!("pan={}c", count),
    }
}

/// Генерирует фильтр atempo для изменения скорости
///
/// # Arguments
/// * `tempo` - множитель скорости (0.5 = в 2 раза медленнее, 2.0 = в 2 раза быстрее)
pub fn tempo(factor: f32) -> String {
    // atempo поддерживает только диапазон 0.5-2.0
    // для больших изменений нужно chain фильтров
    if factor < 0.5 {
        let f1 = (factor * 2.0).max(0.5);
        format!("atempo=0.5,atempo={:.4}", f1)
    } else if factor > 2.0 {
        let f1 = (factor / 2.0).min(2.0);
        format!("atempo=2.0,atempo={:.4}", f1)
    } else {
        format!("atempo={:.4}", factor)
    }
}

/// Объединяет несколько фильтров в цепочку
pub fn chain(filters: &[String]) -> String {
    filters
        .iter()
        .filter(|f| !f.is_empty())
        .cloned()
        .collect::<Vec<_>>()
        .join(",")
}

/// Конвертирует EqPreset в FFmpeg filter string
/// 
/// # Arguments
/// * `preset` - предустановка эквалайзера
/// 
/// # Returns
/// Строка FFmpeg audio filter или пустая строка для Flat
pub fn eq_preset_to_filter(preset: EqPreset) -> String {
    match preset {
        EqPreset::Flat => String::new(),
        EqPreset::BassBoost => {
            // Усиление низких частот: +6dB на 100Hz, ширина 1 октава
            equalizer(100, 'o', 1.0, 6.0)
        }
        EqPreset::Voice => {
            // Highpass для удаления гула + усиление presence (3kHz)
            chain(&[
                highpass(80),
                equalizer(3000, 'o', 1.0, 3.0),
            ])
        }
        EqPreset::Treble => {
            // High shelf boost: +4dB на 8kHz
            equalizer(8000, 'o', 1.5, 4.0)
        }
    }
}

/// Генерирует volume filter из коэффициента (не dB)
/// 
/// # Arguments
/// * `factor` - множитель громкости (1.0 = без изменений, 0.5 = -6dB, 2.0 = +6dB)
/// 
/// # Returns
/// FFmpeg volume filter string или пустая строка для 1.0
pub fn volume_factor(factor: f32) -> String {
    if (factor - 1.0).abs() < 0.001 {
        // Unity gain - без изменений
        String::new()
    } else {
        // Конвертируем в dB: dB = 20 * log10(factor)
        let db = 20.0 * factor.log10();
        volume(db)
    }
}

/// Строит полную цепочку аудио фильтров
/// 
/// # Arguments
/// * `eq_preset` - опциональный EQ preset
/// * `speed` - опциональный множитель скорости (0.5-2.0)
/// * `volume_level` - опциональный множитель громкости (0.0-2.0)
/// 
/// # Returns
/// Полная цепочка FFmpeg audio filters или пустая строка
pub fn build_audio_filter_chain(
    eq_preset: Option<EqPreset>,
    speed: Option<f32>,
    volume_level: Option<f32>,
) -> String {
    let mut filters = Vec::new();
    
    // 1. EQ preset (первым, до изменения скорости)
    if let Some(preset) = eq_preset {
        let eq_filter = eq_preset_to_filter(preset);
        if !eq_filter.is_empty() {
            filters.push(eq_filter);
        }
    }
    
    // 2. Speed (atempo)
    if let Some(s) = speed {
        if (s - 1.0).abs() > 0.001 {
            filters.push(tempo(s));
        }
    }
    
    // 3. Volume (последним, после всех других обработок)
    if let Some(v) = volume_level {
        let vol_filter = volume_factor(v);
        if !vol_filter.is_empty() {
            filters.push(vol_filter);
        }
    }
    
    chain(&filters)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ==================== ВИДЕО ФИЛЬТРЫ ТЕСТЫ ====================

    #[test]
    fn test_transpose_filter_90_degrees() {
        assert_eq!(transpose_filter(90), "transpose=2");
    }

    #[test]
    fn test_transpose_filter_180_degrees() {
        assert_eq!(transpose_filter(180), "transpose=1,transpose=1");
    }

    #[test]
    fn test_transpose_filter_270_degrees() {
        assert_eq!(transpose_filter(270), "transpose=1");
    }

    #[test]
    fn test_transpose_filter_0_degrees() {
        assert_eq!(transpose_filter(0), "");
    }

    #[test]
    fn test_transpose_filter_invalid() {
        // Некорректные значения должны возвращать пустую строку
        assert_eq!(transpose_filter(45), "");
        assert_eq!(transpose_filter(360), "");
    }

    #[test]
    fn test_scale_filter_both_dimensions() {
        assert_eq!(scale_filter(Some(1920), Some(1080)), "scale=1920:1080");
        assert_eq!(scale_filter(Some(1280), Some(720)), "scale=1280:720");
    }

    #[test]
    fn test_scale_filter_width_only() {
        assert_eq!(scale_filter(Some(1920), None), "scale=1920:-2");
        assert_eq!(scale_filter(Some(640), None), "scale=640:-2");
    }

    #[test]
    fn test_scale_filter_height_only() {
        assert_eq!(scale_filter(None, Some(1080)), "scale=-2:1080");
        assert_eq!(scale_filter(None, Some(480)), "scale=-2:480");
    }

    #[test]
    fn test_scale_filter_none() {
        assert_eq!(scale_filter(None, None), "");
    }

    #[test]
    fn test_fps_filter() {
        assert_eq!(fps_filter(30), "fps=30");
        assert_eq!(fps_filter(60), "fps=60");
        assert_eq!(fps_filter(24), "fps=24");
    }

    #[test]
    fn test_chain_video_filters_empty() {
        let filters = vec![];
        assert_eq!(chain_video_filters(&filters), "");
    }

    #[test]
    fn test_chain_video_filters_single() {
        let filters = vec!["transpose=2".to_string()];
        assert_eq!(chain_video_filters(&filters), "transpose=2");
    }

    #[test]
    fn test_chain_video_filters_multiple() {
        let filters = vec![
            "transpose=2".to_string(),
            "scale=1920:1080".to_string(),
            "fps=30".to_string(),
        ];
        let result = chain_video_filters(&filters);
        assert_eq!(result, "transpose=2,scale=1920:1080,fps=30");
    }

    #[test]
    fn test_chain_video_filters_skips_empty() {
        let filters = vec![
            "transpose=2".to_string(),
            String::new(), // Пустой фильтр
            "scale=1920:1080".to_string(),
        ];
        let result = chain_video_filters(&filters);
        assert!(!result.contains(",,"));
        assert_eq!(result, "transpose=2,scale=1920:1080");
    }

    #[test]
    fn test_build_video_filter_chain_orientation_only() {
        let chain = build_video_filter_chain(Some(90), None, None, None);
        assert_eq!(chain, "transpose=2");
    }

    #[test]
    fn test_build_video_filter_chain_scale_only() {
        let chain = build_video_filter_chain(None, Some(1920), Some(1080), None);
        assert_eq!(chain, "scale=1920:1080");
    }

    #[test]
    fn test_build_video_filter_chain_fps_only() {
        let chain = build_video_filter_chain(None, None, None, Some(30));
        assert_eq!(chain, "fps=30");
    }

    #[test]
    fn test_build_video_filter_chain_combined() {
        let chain = build_video_filter_chain(Some(90), Some(1920), Some(1080), Some(30));
        assert_eq!(chain, "transpose=2,scale=1920:1080,fps=30");
    }

    #[test]
    fn test_build_video_filter_chain_orientation_180() {
        let chain = build_video_filter_chain(Some(180), None, None, None);
        assert_eq!(chain, "transpose=1,transpose=1");
    }

    #[test]
    fn test_build_video_filter_chain_orientation_270() {
        let chain = build_video_filter_chain(Some(270), None, None, None);
        assert_eq!(chain, "transpose=1");
    }

    #[test]
    fn test_build_video_filter_chain_orientation_0_skipped() {
        let chain = build_video_filter_chain(Some(0), Some(1920), Some(1080), None);
        // orientation=0 должен быть пропущен
        assert_eq!(chain, "scale=1920:1080");
        assert!(!chain.contains("transpose"));
    }

    #[test]
    fn test_build_video_filter_chain_empty() {
        let chain = build_video_filter_chain(None, None, None, None);
        assert_eq!(chain, "");
    }

    // ==================== АУДИО ФИЛЬТРЫ ТЕСТЫ ====================

    #[test]
    fn test_fade_in() {
        assert_eq!(fade_in(2.0), "afade=t=in:st=0:d=2.00");
        assert_eq!(fade_in(0.5), "afade=t=in:st=0:d=0.50");
    }

    #[test]
    fn test_fade_out() {
        assert_eq!(fade_out(10.0, 2.0), "afade=t=out:st=10.00:d=2.00");
    }

    #[test]
    fn test_loudnorm() {
        let filter = loudnorm(-16.0);
        assert!(filter.contains("loudnorm"));
        assert!(filter.contains("I=-16.0"));
    }

    #[test]
    fn test_volume() {
        assert_eq!(volume(3.0), "volume=3.0dB");
        assert_eq!(volume(-6.0), "volume=-6.0dB");
    }

    #[test]
    fn test_highpass_lowpass() {
        assert_eq!(highpass(100), "highpass=f=100");
        assert_eq!(lowpass(8000), "lowpass=f=8000");
    }

    #[test]
    fn test_tempo() {
        assert_eq!(tempo(1.5), "atempo=1.5000");
        // Проверяем chain для экстремальных значений
        assert!(tempo(0.3).contains("atempo=0.5"));
        assert!(tempo(3.0).contains("atempo=2.0"));
    }

    #[test]
    fn test_chain() {
        let filters = vec![
            fade_in(1.0),
            loudnorm(-16.0),
            String::new(), // Пустой фильтр должен быть пропущен
        ];
        let result = chain(&filters);
        assert!(result.contains("afade"));
        assert!(result.contains("loudnorm"));
        assert!(!result.contains(",,"));
    }

    #[test]
    fn test_channels() {
        assert!(channels(1).contains("mono"));
        assert!(channels(2).contains("stereo"));
    }

    #[test]
    fn test_eq_preset_flat() {
        let filter = eq_preset_to_filter(EqPreset::Flat);
        assert!(filter.is_empty(), "Flat should produce empty filter");
    }

    #[test]
    fn test_eq_preset_bass_boost() {
        let filter = eq_preset_to_filter(EqPreset::BassBoost);
        assert!(filter.contains("equalizer"), "BassBoost should use equalizer");
        assert!(filter.contains("f=100"), "BassBoost should target 100Hz");
    }

    #[test]
    fn test_eq_preset_voice() {
        let filter = eq_preset_to_filter(EqPreset::Voice);
        assert!(filter.contains("highpass"), "Voice should use highpass");
        assert!(filter.contains("equalizer"), "Voice should use equalizer for presence");
    }

    #[test]
    fn test_eq_preset_treble() {
        let filter = eq_preset_to_filter(EqPreset::Treble);
        assert!(filter.contains("equalizer"), "Treble should use equalizer");
        assert!(filter.contains("f=8000"), "Treble should target 8kHz");
    }

    #[test]
    fn test_volume_factor_unity() {
        let filter = volume_factor(1.0);
        assert!(filter.is_empty(), "Volume 1.0 should produce empty filter");
    }

    #[test]
    fn test_volume_factor_amplify() {
        let filter = volume_factor(2.0);
        assert!(filter.contains("volume"), "Volume 2.0 should produce volume filter");
        // 20 * log10(2.0) ≈ 6.02 dB
        assert!(filter.contains("6.0"), "Volume 2.0 should be ~+6dB");
    }

    #[test]
    fn test_volume_factor_attenuate() {
        let filter = volume_factor(0.5);
        assert!(filter.contains("volume"), "Volume 0.5 should produce volume filter");
        // 20 * log10(0.5) ≈ -6.02 dB
        assert!(filter.contains("-6.0"), "Volume 0.5 should be ~-6dB");
    }

    #[test]
    fn test_build_filter_chain_empty() {
        let chain = build_audio_filter_chain(None, None, None);
        assert!(chain.is_empty(), "No filters should produce empty chain");
    }

    #[test]
    fn test_build_filter_chain_speed_only() {
        let chain = build_audio_filter_chain(None, Some(1.5), None);
        assert!(chain.contains("atempo"), "Speed should add atempo filter");
        assert!(chain.contains("1.5"), "Speed 1.5 should be in filter");
    }

    #[test]
    fn test_build_filter_chain_combined() {
        let chain = build_audio_filter_chain(
            Some(EqPreset::BassBoost),
            Some(1.25),
            Some(0.8),
        );
        assert!(chain.contains("equalizer"), "Should have EQ");
        assert!(chain.contains("atempo"), "Should have speed");
        assert!(chain.contains("volume"), "Should have volume");
        // Проверяем порядок: EQ, speed, volume
        let eq_pos = chain.find("equalizer").unwrap();
        let tempo_pos = chain.find("atempo").unwrap();
        let vol_pos = chain.find("volume").unwrap();
        assert!(eq_pos < tempo_pos, "EQ should come before tempo");
        assert!(tempo_pos < vol_pos, "Tempo should come before volume");
    }
}
