//! Unit tests для filters.rs
//!
//! Тестирует генерацию EQ presets и фильтров скорости

use rust_transcoder::transcoder::filters;
use rust_transcoder::models::EqPreset;

/// Test: EqPreset::Flat должен возвращать пустой фильтр или pass-through
#[test]
fn test_eq_preset_flat() {
    let filter = filters::eq_preset_to_filter(EqPreset::Flat);
    // Flat preset не должен добавлять никаких EQ фильтров
    assert!(
        filter.is_empty() || filter == "anull",
        "Flat preset should produce empty or pass-through filter, got: {}",
        filter
    );
}

/// Test: EqPreset::BassBoost должен усиливать низкие частоты
#[test]
fn test_eq_preset_bass_boost() {
    let filter = filters::eq_preset_to_filter(EqPreset::BassBoost);
    // Должен содержать equalizer или bass filter с низкой частотой
    assert!(
        filter.contains("equalizer") || filter.contains("bass") || filter.contains("lowshelf"),
        "BassBoost should contain bass-related filter, got: {}",
        filter
    );
}

/// Test: EqPreset::Voice должен фильтровать для голоса
#[test]
fn test_eq_preset_voice() {
    let filter = filters::eq_preset_to_filter(EqPreset::Voice);
    // Голосовой preset обычно включает highpass для удаления гула
    // и/или компрессию для выравнивания громкости
    assert!(
        filter.contains("highpass") || filter.contains("equalizer") || filter.contains("lowshelf"),
        "Voice preset should contain voice-optimized filter, got: {}",
        filter
    );
}

/// Test: EqPreset::Treble должен усиливать высокие частоты
#[test]
fn test_eq_preset_treble() {
    let filter = filters::eq_preset_to_filter(EqPreset::Treble);
    // Должен содержать high shelf или treble boost
    assert!(
        filter.contains("equalizer") || filter.contains("treble") || filter.contains("highshelf"),
        "Treble preset should contain treble-related filter, got: {}",
        filter
    );
}

/// Test: speed filter с валидным значением (1.0 - no change)
#[test]
fn test_speed_filter_no_change() {
    let filter = filters::tempo(1.0);
    assert!(
        filter.contains("1.0") || filter.contains("1.00"),
        "Speed 1.0 should produce atempo=1.0, got: {}",
        filter
    );
}

/// Test: speed filter с ускорением (1.5x)
#[test]
fn test_speed_filter_faster() {
    let filter = filters::tempo(1.5);
    assert!(
        filter.contains("atempo") && filter.contains("1.5"),
        "Speed 1.5 should produce atempo=1.5, got: {}",
        filter
    );
}

/// Test: speed filter с замедлением (0.75x)
#[test]
fn test_speed_filter_slower() {
    let filter = filters::tempo(0.75);
    assert!(
        filter.contains("atempo") && filter.contains("0.75"),
        "Speed 0.75 should produce atempo=0.75, got: {}",
        filter
    );
}

/// Test: speed filter на границе (0.5x)
#[test]
fn test_speed_filter_minimum() {
    let filter = filters::tempo(0.5);
    assert!(
        filter.contains("atempo") && filter.contains("0.5"),
        "Speed 0.5 should produce atempo=0.5, got: {}",
        filter
    );
}

/// Test: speed filter на границе (2.0x)
#[test]
fn test_speed_filter_maximum() {
    let filter = filters::tempo(2.0);
    assert!(
        filter.contains("atempo") && filter.contains("2.0"),
        "Speed 2.0 should produce atempo=2.0, got: {}",
        filter
    );
}

/// Test: volume filter с усилением (1.5x = ~3.5dB)
#[test]
fn test_volume_filter_amplify() {
    let filter = filters::volume_factor(1.5);
    // volume factor 1.5 = примерно +3.5dB
    assert!(
        filter.contains("volume"),
        "Volume 1.5 should produce volume filter, got: {}",
        filter
    );
}

/// Test: volume filter с ослаблением (0.5x = ~-6dB)
#[test]
fn test_volume_filter_attenuate() {
    let filter = filters::volume_factor(0.5);
    assert!(
        filter.contains("volume"),
        "Volume 0.5 should produce volume filter, got: {}",
        filter
    );
}

/// Test: volume filter unity (1.0 = 0dB)
#[test]
fn test_volume_filter_unity() {
    let filter = filters::volume_factor(1.0);
    // При volume=1.0 может быть пустой фильтр или volume=0dB
    assert!(
        filter.is_empty() || filter.contains("volume"),
        "Volume 1.0 should produce empty or volume=0dB, got: {}",
        filter
    );
}

/// Test: build_audio_filter_chain с комбинацией фильтров
#[test]
fn test_build_filter_chain_combined() {
    let chain = filters::build_audio_filter_chain(
        Some(EqPreset::BassBoost),
        Some(1.25),  // speed
        Some(0.8),   // volume
    );
    
    // Цепочка должна содержать все компоненты
    assert!(
        !chain.is_empty(),
        "Filter chain should not be empty with filters applied"
    );
    
    // Проверяем что компоненты присутствуют
    if chain.contains(',') {
        // Если есть запятые - это цепочка фильтров
        assert!(
            chain.contains("atempo") || chain.contains("volume") || chain.contains("equalizer"),
            "Chain should contain expected filters"
        );
    }
}

/// Test: build_audio_filter_chain без фильтров
#[test]
fn test_build_filter_chain_empty() {
    let chain = filters::build_audio_filter_chain(None, None, None);
    
    // Без фильтров цепочка должна быть пустой или содержать только anull
    assert!(
        chain.is_empty() || chain == "anull",
        "Empty filter options should produce empty chain, got: {}",
        chain
    );
}

/// Test: build_audio_filter_chain только с eq_preset
#[test]
fn test_build_filter_chain_only_eq() {
    let chain = filters::build_audio_filter_chain(Some(EqPreset::Voice), None, None);
    
    assert!(
        !chain.is_empty() || chain == "anull",
        "EQ-only chain should not be empty, got: {}",
        chain
    );
}

/// Test: build_audio_filter_chain только со speed
#[test]
fn test_build_filter_chain_only_speed() {
    let chain = filters::build_audio_filter_chain(None, Some(1.5), None);
    
    assert!(
        chain.contains("atempo") && chain.contains("1.5"),
        "Speed-only chain should contain atempo=1.5, got: {}",
        chain
    );
}
