//! Orientation correction filter tests
//!
//! Тестирует генерацию видео фильтров для коррекции ориентации

use rust_transcoder::transcoder::filters;

/// Test: orientation 90 градусов должен использовать transpose=2
#[test]
fn test_orientation_90_degrees() {
    let filter = filters::transpose_filter(90);
    assert_eq!(
        filter,
        "transpose=2",
        "90° CCW should use transpose=2, got: {}",
        filter
    );
}

/// Test: orientation 180 градусов должен использовать двойной transpose
#[test]
fn test_orientation_180_degrees() {
    let filter = filters::transpose_filter(180);
    assert_eq!(
        filter,
        "transpose=1,transpose=1",
        "180° should use transpose=1,transpose=1, got: {}",
        filter
    );
}

/// Test: orientation 270 градусов должен использовать transpose=1
#[test]
fn test_orientation_270_degrees() {
    let filter = filters::transpose_filter(270);
    assert_eq!(
        filter,
        "transpose=1",
        "270° CCW (90° CW) should use transpose=1, got: {}",
        filter
    );
}

/// Test: orientation 0 градусов не должен применять фильтр
#[test]
fn test_orientation_0_degrees() {
    let filter = filters::transpose_filter(0);
    assert!(
        filter.is_empty(),
        "0° orientation should produce empty filter, got: {}",
        filter
    );
}

/// Test: некорректные значения ориентации должны возвращать пустую строку
#[test]
fn test_orientation_invalid_values() {
    // Некорректные углы
    let invalid_angles = [45, 135, 225, 315, 360, 720];

    for angle in invalid_angles {
        let filter = filters::transpose_filter(angle);
        assert!(
            filter.is_empty(),
            "Invalid orientation {} should produce empty filter, got: {}",
            angle,
            filter
        );
    }
}

/// Test: scale filter с обеими размерностями
#[test]
fn test_scale_filter_both_dimensions() {
    let filter = filters::scale_filter(Some(1920), Some(1080));
    assert_eq!(
        filter, "scale=1920:1080",
        "Scale with both dimensions should be scale=W:H, got: {}",
        filter
    );
}

/// Test: scale filter только с шириной
#[test]
fn test_scale_filter_width_only() {
    let filter = filters::scale_filter(Some(1280), None);
    assert_eq!(
        filter, "scale=1280:-2",
        "Scale with width only should use -2 for height, got: {}",
        filter
    );
}

/// Test: scale filter только с высотой
#[test]
fn test_scale_filter_height_only() {
    let filter = filters::scale_filter(None, Some(720));
    assert_eq!(
        filter, "scale=-2:720",
        "Scale with height only should use -2 for width, got: {}",
        filter
    );
}

/// Test: scale filter без параметров
#[test]
fn test_scale_filter_no_dimensions() {
    let filter = filters::scale_filter(None, None);
    assert!(
        filter.is_empty(),
        "Scale with no dimensions should be empty, got: {}",
        filter
    );
}

/// Test: fps filter
#[test]
fn test_fps_filter() {
    let filter = filters::fps_filter(30);
    assert!(
        filter.contains("fps=30"),
        "FPS filter should contain fps=30, got: {}",
        filter
    );
}

/// Test: объединение видео фильтров в цепочку
#[test]
fn test_chain_video_filters() {
    let filters = vec![
        "transpose=2".to_string(),
        "scale=1920:1080".to_string(),
        "fps=30".to_string(),
    ];

    let chain = filters::chain_video_filters(&filters);
    assert_eq!(
        chain, "transpose=2,scale=1920:1080,fps=30",
        "Video filters should be chained with commas, got: {}",
        chain
    );
}

/// Test: пустые фильтры должны пропускаться при объединении
#[test]
fn test_chain_video_filters_skip_empty() {
    let filters = vec![
        "transpose=2".to_string(),
        String::new(), // Пустой фильтр
        "scale=1920:1080".to_string(),
    ];

    let chain = filters::chain_video_filters(&filters);
    assert!(
        !chain.contains(",,"),
        "Chain should not contain double commas, got: {}",
        chain
    );
    assert_eq!(
        chain, "transpose=2,scale=1920:1080",
        "Empty filters should be skipped, got: {}",
        chain
    );
}

/// Test: build_video_filter_chain только с ориентацией
#[test]
fn test_build_video_filter_chain_orientation_only() {
    let chain = filters::build_video_filter_chain(Some(90), None, None, None);
    assert_eq!(
        chain, "transpose=2",
        "Orientation-only chain should contain transpose filter, got: {}",
        chain
    );
}

/// Test: build_video_filter_chain только с масштабированием
#[test]
fn test_build_video_filter_chain_scale_only() {
    let chain = filters::build_video_filter_chain(None, Some(1920), Some(1080), None);
    assert_eq!(
        chain, "scale=1920:1080",
        "Scale-only chain should contain scale filter, got: {}",
        chain
    );
}

/// Test: build_video_filter_chain только с FPS
#[test]
fn test_build_video_filter_chain_fps_only() {
    let chain = filters::build_video_filter_chain(None, None, None, Some(30));
    assert_eq!(
        chain, "fps=30",
        "FPS-only chain should contain fps filter, got: {}",
        chain
    );
}

/// Test: build_video_filter_chain с комбинацией фильтров
#[test]
fn test_build_video_filter_chain_combined() {
    let chain = filters::build_video_filter_chain(Some(90), Some(1920), Some(1080), Some(30));

    // Проверяем наличие всех компонентов
    assert!(
        chain.contains("transpose"),
        "Combined chain should contain transpose filter, got: {}",
        chain
    );
    assert!(
        chain.contains("scale"),
        "Combined chain should contain scale filter, got: {}",
        chain
    );
    assert!(
        chain.contains("fps"),
        "Combined chain should contain fps filter, got: {}",
        chain
    );

    // Проверяем порядок: orientation -> scale -> fps
    assert_eq!(
        chain, "transpose=2,scale=1920:1080,fps=30",
        "Filters should be in correct order, got: {}",
        chain
    );
}

/// Test: build_video_filter_chain с orientation=0 должен пропускать transpose
#[test]
fn test_build_video_filter_chain_skip_zero_orientation() {
    let chain = filters::build_video_filter_chain(Some(0), Some(1920), Some(1080), None);

    assert!(
        !chain.contains("transpose"),
        "orientation=0 should skip transpose filter, got: {}",
        chain
    );
    assert!(
        chain.contains("scale"),
        "Chain should still contain scale filter, got: {}",
        chain
    );
}

/// Test: build_video_filter_chain без фильтров
#[test]
fn test_build_video_filter_chain_empty() {
    let chain = filters::build_video_filter_chain(None, None, None, None);

    assert!(
        chain.is_empty(),
        "Chain with no filters should be empty, got: {}",
        chain
    );
}

/// Test: orientation 180 + scale
#[test]
fn test_orientation_180_with_scale() {
    let chain = filters::build_video_filter_chain(Some(180), Some(1280), Some(720), None);

    assert_eq!(
        chain, "transpose=1,transpose=1,scale=1280:720",
        "180° rotation with scale should have both filters, got: {}",
        chain
    );
}

/// Test: orientation 270 + scale + fps
#[test]
fn test_orientation_270_full_chain() {
    let chain = filters::build_video_filter_chain(Some(270), Some(1920), Some(1080), Some(60));

    assert_eq!(
        chain, "transpose=1,scale=1920:1080,fps=60",
        "270° rotation with scale and fps should have all filters, got: {}",
        chain
    );
}

/// Test: mobile видео (portrait) - orientation 90
#[test]
fn test_mobile_video_portrait_90() {
    // Портретное видео с телефона (повёрнуто на 90° против часовой)
    let chain = filters::build_video_filter_chain(Some(90), None, Some(1920), None);

    assert!(
        chain.contains("transpose=2"),
        "Mobile portrait video should use transpose=2, got: {}",
        chain
    );
    assert!(
        chain.contains("scale"),
        "Should contain scale filter for height adjustment, got: {}",
        chain
    );
}

/// Test: mobile видео (portrait) - orientation 270
#[test]
fn test_mobile_video_portrait_270() {
    // Портретное видео с телефона (повёрнуто на 270° против часовой = 90° по часовой)
    let chain = filters::build_video_filter_chain(Some(270), None, Some(1920), None);

    assert!(
        chain.contains("transpose=1"),
        "Mobile portrait video (270°) should use transpose=1, got: {}",
        chain
    );
}

/// Test: verification - коррекция ориентации для разных сценариев
#[test]
fn test_orientation_correction_scenarios() {
    // iOS видео (обычно 90° CCW)
    let ios_filter = filters::transpose_filter(90);
    assert_eq!(ios_filter, "transpose=2");

    // Android видео (иногда 270° CCW)
    let android_filter = filters::transpose_filter(270);
    assert_eq!(android_filter, "transpose=1");

    // Upside down видео (180°)
    let upside_down_filter = filters::transpose_filter(180);
    assert_eq!(upside_down_filter, "transpose=1,transpose=1");

    // Нормальное видео (0°)
    let normal_filter = filters::transpose_filter(0);
    assert!(normal_filter.is_empty());
}
