import fs from 'fs/promises';
import path from 'path';

const HIGH_RISK_ACTIONS = {
    'frappe/core': ['putUser', 'postUser'],
    'frappe/website': ['putWebsiteSettings'],
    'frappe/email': ['putEmailAccount'],
    'erpnext/accounts': ['putSubscriptionPlan', 'postSubscriptionPlan', 'putProcessSubscription'],
    'control/control': [
        'putPaystackSettings', 'putStorageSettings', 'putSubscriptionSettings',
        'putSwaggerSettings', 'putTenantEmailSettings', 'putTenderControlSettings',
        'putWeatherSettings', 'postCompanySubscription', 'putCompanySubscription', 'deleteCompanySubscription'
    ]
};

const AUTH_ACTIONS = {
    'frappe/auth': ['getLoggedUserDetails', 'login', 'logout']
};

const BASE_AI_PATH = path.join('nextjs_frontend', 'ai');
const LIB_ACTIONS_PATH = path.join('nextjs_frontend', 'lib', 'actions');
const AUTH_ACTIONS_PATH = path.join('nextjs_frontend', 'app', '(auth)', 'actions');

async function updateImportPaths(oldPath, newPath) {
    const projectDir = 'nextjs_frontend';
    const files = await fs.readdir(projectDir, { recursive: true });
    for (const file of files) {
        const filePath = path.join(projectDir, file);
        if (filePath.endsWith('.ts') || filePath.endsWith('.tsx')) {
            try {
                let content = await fs.readFile(filePath, 'utf-8');
                const oldImportPath = oldPath.replace(/\\/g, '/').replace('nextjs_frontend/', '@/');
                const newImportPath = newPath.replace(/\\/g, '/').replace('nextjs_frontend/', '@/');
                if (content.includes(oldImportPath)) {
                    content = content.replace(new RegExp(oldImportPath, 'g'), newImportPath);
                    await fs.writeFile(filePath, content);
                    console.log(`Updated import in: ${filePath}`);
                }
            } catch (error) {
                console.error(`Error processing file ${filePath}:`, error);
            }
        }
    }
}

async function moveAction(actionPath, destinationPath) {
    try {
        // Ensure the source exists before we do anything
        await fs.access(actionPath);

        // Copy directory recursively
        await fs.cp(actionPath, destinationPath, { recursive: true });

        // Update import paths
        await updateImportPaths(actionPath, destinationPath);

        // Remove the original directory
        await fs.rm(actionPath, { recursive: true, force: true });

        console.log(`Moved: ${path.basename(actionPath)} to ${destinationPath}`);
    } catch (error) {
        if (error.code === 'ENOENT') {
            console.warn(`Warning: Action not found, skipping: ${actionPath}`);
        } else {
            console.error(`Error moving ${actionPath}:`, error);
        }
    }
}

async function organizeActions() {
    console.log('--- Starting Server Action Organization ---');

    // Move High-Risk Actions
    for (const [modulePath, actions] of Object.entries(HIGH_RISK_ACTIONS)) {
        for (const action of actions) {
            // Path correction logic
            const pathParts = modulePath.split('/');
            const appName = pathParts[0];
            const moduleName = pathParts.length > 1 ? pathParts[1] : '';

            // The 'frappe' app has a flat structure in the 'ai' directory
            const sourcePath = appName === 'frappe'
                ? path.join(BASE_AI_PATH, appName, moduleName, action)
                : path.join(BASE_AI_PATH, appName, appName, moduleName, action); // Other apps have a nested structure

            const destPath = path.join(LIB_ACTIONS_PATH, appName, moduleName, action);
            await moveAction(sourcePath, destPath);
        }
    }

    // Move Auth Actions
    for (const [modulePath, actions] of Object.entries(AUTH_ACTIONS)) {
         for (const action of actions) {
            const [appName, moduleName] = modulePath.split('/');
            const sourcePath = path.join(BASE_AI_PATH, appName, moduleName, action);
            const destPath = path.join(AUTH_ACTIONS_PATH, action);
            await moveAction(sourcePath, destPath);
        }
    }

    console.log('--- Server Action Organization Complete ---');
}

organizeActions();
