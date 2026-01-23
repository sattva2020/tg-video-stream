module.exports = function(api) {
  api.cache(true);
  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel'
    ],
    plugins: [
      'react-native-reanimated/plugin',
      [
        'module-resolver',
        {
          alias: {
            '@': './src',
            '@/components': './src/components',
            '@/screens': './src/screens',
            '@/navigation': './src/navigation',
            '@/api': './src/api',
            '@/hooks': './src/hooks',
            '@/contexts': './src/contexts',
            '@/utils': './src/utils',
            '@/i18n': './src/i18n',
            '@/assets': './assets'
          }
        }
      ]
    ],
    env: {
      production: {
        plugins: ['react-native-paper/babel-plugin-rtl-support']
      }
    }
  };
};
