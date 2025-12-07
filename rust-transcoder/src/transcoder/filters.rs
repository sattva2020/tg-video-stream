//! Аудио фильтры FFmpeg
//!
//! Генерация строк фильтров для FFmpeg -af опции.

use crate::models::EqPreset;

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
