import stylistic from '@stylistic/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

export default [
    { ignores: ['dist/**'] },
    {
        files: ['**/*.{js,mjs,ts,tsx}'],
        languageOptions: { parser: tsParser },
        plugins: { '@stylistic': stylistic },
        rules: {
            '@stylistic/indent': ['error', 4],
            '@stylistic/no-tabs': 'error',
        },
    },
];
