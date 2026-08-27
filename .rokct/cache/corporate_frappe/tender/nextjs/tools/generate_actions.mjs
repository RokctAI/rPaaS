import fs from 'fs/promises';
import path from 'path';

// Helper to convert strings to PascalCase for schema/type names
function toPascalCase(str) {
  const cleanStr = str.replace(/%20/g, ' ');
  return cleanStr.replace(/(?:^\w|[A-Z]|\b\w)/g, (word) => {
    return word.toUpperCase();
  }).replace(/\s+/g, '');
}

// Maps Swagger/OpenAPI data types to Zod schema types
function getZodType(property) {
    if (!property) return 'z.any()';
    if (property.$ref) return 'z.any()';

    switch (property.type) {
        case 'string':
            if (property.format === 'date' || property.format === 'date-time') {
                return 'z.string()';
            }
            return 'z.string()';
        case 'integer':
        case 'number':
            return 'z.number()';
        case 'boolean':
            return 'z.boolean()';
        case 'array':
            if (property.items && property.items.properties) {
                const nestedProperties = Object.entries(property.items.properties)
                    .map(([key, value]) => `"${key}": ${getZodType(value)}`)
                    .join(', ');
                return `z.array(z.object({${nestedProperties}}))`;
            } else if (property.items) {
                const itemType = getZodType(property.items);
                return `z.array(${itemType})`;
            }
            return 'z.array(z.any())';
        case 'object':
             if (!property.properties) {
                return 'z.any()';
             }
             const nestedProperties = Object.entries(property.properties)
                .map(([key, value]) => `"${key}": ${getZodType(value)}`)
                .join(', ');
             return `z.object({${nestedProperties}})`;
        default:
            return 'z.any()';
    }
}

// Extracts the schema definition for a given operation
function getSchemaDefinition(operation) {
    if (operation?.requestBody?.content?.['application/json']?.schema?.properties) {
        return operation.requestBody.content['application/json'].schema.properties;
    }
    if (operation?.responses?.['200']?.content?.['application/json']?.schema?.properties?.data?.properties) {
        return operation.responses['200'].content['application/json'].schema.properties.data.properties;
    }
    if (operation?.responses?.['200']?.content?.['application/json']?.schema?.properties?.data?.items?.properties) {
        return operation.responses['200'].content['application/json'].schema.properties.data.items.properties;
    }
    if (operation?.responses?.['200']?.content?.['application/json']?.schema?.properties?.data) {
        if (operation.responses['200'].content['application/json'].schema.properties.data.properties) {
             return operation.responses['200'].content['application/json'].schema.properties.data.properties;
        }
    }
    if (operation?.responses?.['200']?.content?.['application/json']?.schema?.properties) {
         return operation.responses['200'].content['application/json'].schema.properties;
    }
    return null;
}

function generateSmartActionContent(functionName, method, schemaDefinition, apiPath, operation) {
    let zodSchema = '';
    let typeExport = '';
    let functionParams = '';
    let functionReturn = 'Promise<any>';
    let fetchBody = '';

    if (schemaDefinition) {
        let schemaProps = Object.entries(schemaDefinition)
            .map(([prop, value]) => {
                const isOptional = !operation.requestBody?.required && !value.required;
                return `  "${prop}": ${getZodType(value)}${isOptional ? '.optional()' : ''}`;
            })
            .join(',\n');

        zodSchema = `const ${functionName}Schema = z.object({\n${schemaProps}\n});`;
        typeExport = `export type ${functionName}Input = z.infer<typeof ${functionName}Schema>;`;
        functionParams = `input: ${functionName}Input, apiKey: string, apiSecret: string`;
        fetchBody = `body: JSON.stringify(input),`;
    } else {
        zodSchema = `const ${functionName}Schema = z.any();`;
        typeExport = `export type ${functionName}Input = any;`;
        functionParams = `input: any, apiKey: string, apiSecret: string`;
    }

    return `
"use server";
import { z } from "zod";

${zodSchema}

${typeExport}

export async function ${functionName}(${functionParams}): ${functionReturn} {
  const response = await fetch(\`${apiPath}\`, {
    method: "${method.toUpperCase()}",
    headers: {
      "Authorization": \`token \${apiKey}:\${apiSecret}\`,
      "Content-Type": "application/json",
    },
    ${fetchBody}
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(\`Failed to execute ${functionName}: \${errorBody}\`);
  }

  const result = await response.json();
  return result.message || result.data;
}`;
}

function generateFileContent(pascalCaseDocType, method, docType, schemaDefinition, apiPath, operation) {
    const camelCaseDocType = pascalCaseDocType.charAt(0).toLowerCase() + pascalCaseDocType.slice(1);

    let zodSchema = '';
    let typeExport = '';
    let functionParams = '';
    let functionReturn = '';
    let fetchUrl = '';
    let requestBody = '';
    let actionName = '';

    if (method !== 'delete' && schemaDefinition) {
        let schemaProps = Object.entries(schemaDefinition)
            .filter(([prop, value]) => !value.readOnly)
            .map(([prop, value]) => `  "${prop}": ${getZodType(value)}.optional()`)
            .join(',\n');

        if (method === 'put' || method === 'post') {
            const hasWritableName = schemaDefinition.name && !schemaDefinition.name.readOnly;
            if (!hasWritableName) {
                 if (!schemaDefinition.name) {
                    schemaProps = `  "name": z.string().optional(),\n${schemaProps}`;
                 }
            }
        }
        
        if (schemaProps.trim() !== '') {
            zodSchema = `const ${pascalCaseDocType}Schema = z.object({\n${schemaProps}\n});`;
            typeExport = `export type ${pascalCaseDocType} = z.infer<typeof ${pascalCaseDocType}Schema>;`;
        } else if (method !== 'get') {
            zodSchema = `const ${pascalCaseDocType}Schema = z.object({});`;
            typeExport = `export type ${pascalCaseDocType} = z.infer<typeof ${pascalCaseDocType}Schema>;`;
        }

    } else if (method !== 'delete' && !schemaDefinition) {
        console.warn(`No schema found for ${method.toUpperCase()} ${apiPath}. Using z.any()`);
        zodSchema = `const ${pascalCaseDocType}Schema = z.any();`;
        typeExport = `export type ${pascalCaseDocType} = z.infer<typeof ${pascalCaseDocType}Schema>;`;
    }

    if (!typeExport && method === 'get') {
        zodSchema = `const ${pascalCaseDocType}Schema = z.any();`;
        typeExport = `export type ${pascalCaseDocType} = z.infer<typeof ${pascalCaseDocType}Schema>;`;
    }

    const operationId = operation.operationId;
    const useMethodApi = operationId && operationId.startsWith('/');

    switch (method) {
      case 'get':
        actionName = `get${pascalCaseDocType}`;
        if (apiPath.includes('{name}')) {
          functionParams = `name: string, apiKey: string, apiSecret: string`;
          functionReturn = `Promise<${pascalCaseDocType}>`;
          if (useMethodApi) {
            fetchUrl = `\`\${'${operationId}'}?name=\${encodeURIComponent(name)}\``;
          } else {
            fetchUrl = `\`/api/v1/resource/${docType}/\${encodeURIComponent(name)}\``;
          }
        } else {
          functionParams = `apiKey: string, apiSecret: string`;
          functionReturn = `Promise<${pascalCaseDocType}>`;
          if (useMethodApi) {
            fetchUrl = `\`${operationId}\``;
          } else {
            fetchUrl = `\`/api/v1/resource/${docType}\``;
          }
        }
        break;
      case 'post':
        actionName = `create${pascalCaseDocType}`;
        functionParams = `doc: ${pascalCaseDocType}, apiKey: string, apiSecret: string`;
        functionReturn = `Promise<${pascalCaseDocType}>`;
        if (useMethodApi) {
          fetchUrl = `\`${operationId}\``;
        } else {
          fetchUrl = `\`/api/v1/resource/${docType}\``;
        }
        requestBody = `body: JSON.stringify(doc),`;
        break;
      case 'put':
        actionName = `update${pascalCaseDocType}`;
        if (apiPath.includes('{name}')) {
          functionParams = `name: string, doc: Partial<${pascalCaseDocType}>, apiKey: string, apiSecret: string`;
          functionReturn = `Promise<${pascalCaseDocType}>`;
          if (useMethodApi) {
             fetchUrl = `\`\${'${operationId}'}?name=\${encodeURIComponent(name)}\``;
          } else {
            fetchUrl = `\`/api/v1/resource/${docType}/\${encodeURIComponent(name)}\``;
          }
        } else {
          functionParams = `doc: Partial<${pascalCaseDocType}>, apiKey: string, apiSecret: string`;
          functionReturn = `Promise<${pascalCaseDocType}>`;
           if (useMethodApi) {
             fetchUrl = `\`${operationId}\``;
           } else {
             fetchUrl = `\`/api/v1/resource/${docType}\``;
           }
        }
        requestBody = `body: JSON.stringify(doc),`;
        break;
      case 'delete':
        actionName = `delete${pascalCaseDocType}`;
        functionParams = `name: string, apiKey: string, apiSecret: string`;
        functionReturn = `Promise<void>`;
        if (useMethodApi) {
            fetchUrl = `\`\${'${operationId}'}?name=\${encodeURIComponent(name)}\``;
        } else {
            fetchUrl = `\`/api/v1/resource/${docType}/\${encodeURIComponent(name)}\``;
        }
        zodSchema = '';
        typeExport = '';
        break;
    }

    const fileContent = `
"use server";
${zodSchema ? 'import { z } from "zod";' : ''}

${zodSchema}

${typeExport}

export async function ${actionName}(${functionParams}): ${functionReturn} {
  const response = await fetch(${fetchUrl}, {
    method: "${method.toUpperCase()}",
    headers: {
      "Authorization": \`token \${apiKey}:\${apiSecret}\`,
      "X-Action-Source": "AI",
      "Content-Type": "application/json",
    },
    ${requestBody}
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(\`Failed to ${actionName.replace(/([A-Z])/g, ' $1').toLowerCase()}: \${errorBody}\`);
  }
  
  ${method === 'delete' ? 'return;' : ''}
  
  const result = await response.json();
  return result.data;
}`;
    return { fileContent, actionName };
}

async function generateActionsForSwaggerFile(swaggerFilePath, appName, moduleName, smartDocTypes) {
  const swaggerFileContent = await fs.readFile(swaggerFilePath, 'utf-8');
  const swaggerSpec = JSON.parse(swaggerFileContent);

  // Treat the app's main module (e.g., control) as the AI Smart Wrapper module
  const isAIModule = moduleName === appName || moduleName === "ai" || moduleName === "ai_endpoints";

  let expectedActions = 0;
  let generatedActions = 0;
  const barrelExports = [];

  for (const apiPath in swaggerSpec.paths) {
    for (const method in swaggerSpec.paths[apiPath]) {
      const operation = swaggerSpec.paths[apiPath][method];

      if (isAIModule) {
          const functionName = toPascalCase(operation.summary);
          const schemaDefinition = operation.requestBody?.content?.['application/json']?.schema?.properties;

          const fileContent = generateSmartActionContent(functionName, method, schemaDefinition, apiPath, operation);

          const actionDir = path.join('nextjs_frontend', 'ai', appName, 'smart_actions', functionName);
          await fs.mkdir(actionDir, { recursive: true });
          await fs.writeFile(path.join(actionDir, 'actions.ts'), fileContent.trim());
          console.log(`🚀 Generated Smart Action: ${functionName}`);
          generatedActions++;
          continue;
      }

      const tagName = operation.tags && operation.tags[0];

      if (!tagName || !['get', 'post', 'put', 'delete'].includes(method)) continue;

      if (method === 'get' && !apiPath.includes('{name}') && operation.parameters && operation.parameters.some(p => p.name === 'limit_start')) {
          continue;
      }
      
      expectedActions++;

      const docTypeMatch = tagName.match(/^(.*) DocType/);
      if (!docTypeMatch) {
          console.warn(`Could not parse DocType from tag: "${tagName}". Skipping ${method.toUpperCase()} ${apiPath}`);
          continue;
      }

      const docTypeRaw = docTypeMatch[1];
      const docTypeUrl = docTypeRaw.replace(/ /g, '%20');
      const pascalCaseDocType = toPascalCase(docTypeRaw);

      // --- SMART ACTION CHECK ---
      // If we are generating a POST (create) action, and a Smart Wrapper exists for this DocType, SKIP IT.
      if (method === 'post' && smartDocTypes && smartDocTypes.has(pascalCaseDocType)) {
          console.log(`Skipping standard POST for ${pascalCaseDocType} (Smart Wrapper exists)`);
          // We count it as "generated" to verify the expected actions count,
          // OR we decrement expectedActions?
          // Let's just log it and continue. The verification logic compares expectedActions vs generatedActions.
          // If we skip, generatedActions won't increment.
          // So we should decrement expectedActions.
          expectedActions--;
          continue;
      }

      const schemaDefinition = getSchemaDefinition(operation);
      
      if (!schemaDefinition && method !== 'delete') {
          console.warn(`No schema definition found for ${method.toUpperCase()} ${apiPath}. Skipping.`);
          continue;
      }

      const { fileContent, actionName: functionName } = generateFileContent(pascalCaseDocType, method, docTypeUrl, schemaDefinition, apiPath, operation);
      const actionFolderName = `${method}${pascalCaseDocType}`;

      const actionDir = path.join('nextjs_frontend', 'ai', appName, moduleName, actionFolderName);
      await fs.mkdir(actionDir, { recursive: true });
      await fs.writeFile(path.join(actionDir, 'actions.ts'), fileContent.trim());
      console.log(`Generated ${actionFolderName} in ${moduleName}`);
      generatedActions++;

      barrelExports.push(`export * from './${actionFolderName}/actions';`);
    }
  }

  if (barrelExports.length > 0) {
    const barrelFilePath = path.join('nextjs_frontend', 'ai', appName, moduleName, 'index.ts');
    barrelExports.sort();
    const barrelFileContent = barrelExports.join('\n') + '\n';
    await fs.writeFile(barrelFilePath, barrelFileContent);
    console.log(`Created barrel file for module: ${moduleName}`);
  }

  console.log(`\nVerification for module: ${moduleName}`);
  console.log(`Total operations processed: ${expectedActions}`);
  console.log(`Generated action files: ${generatedActions}`);
}

async function getSmartDocTypes(swaggerDir, appName) {
    const smartDocTypes = new Set();
    try {
        const files = await fs.readdir(swaggerDir);
        // Find module-control-control.json (new) or legacy ai/ai_endpoints
        const aiFile = files.find(f =>
            (f.includes(`module-${appName}-${appName}.json`) || f.includes(`module-${appName}-ai.json`) || f.includes(`module-${appName}-ai_endpoints`))
            && f.endsWith('.json')
        );

        if (aiFile) {
            const content = await fs.readFile(path.join(swaggerDir, aiFile), 'utf-8');
            const spec = JSON.parse(content);
            for (const pathKey in spec.paths) {
                for (const method in spec.paths[pathKey]) {
                    const summary = spec.paths[pathKey][method].summary; // e.g. "Create Smart Sales Order"
                    if (summary && summary.startsWith("Create Smart ")) {
                        const rawDocType = summary.replace("Create Smart ", "");
                        smartDocTypes.add(toPascalCase(rawDocType));
                    }
                }
            }
            console.log(`🎯 Found ${smartDocTypes.size} Smart Wrappers. Standard POST actions will be skipped for:`, Array.from(smartDocTypes).join(", "));
        } else {
            console.log("No Smart Wrapper file found. All standard actions will be generated.");
        }
    } catch (e) {
        console.warn("Could not pre-scan for Smart Wrappers:", e.message);
    }
    return smartDocTypes;
}

async function main() {
  const appName = process.argv[2]; 
  if (!appName) {
    console.error("Please provide an app name as an argument.");
    process.exit(1);
  }

  const swaggerDir = path.join('Analyze', 'swagger', appName);
  let swaggerFiles;

  try {
    swaggerFiles = await fs.readdir(swaggerDir);
  } catch (error) {
    console.error(`Error reading directory ${swaggerDir}:`, error.message);
    process.exit(1);
  }

  // PRE-SCAN FOR SMART WRAPPERS
  const smartDocTypes = await getSmartDocTypes(swaggerDir, appName);

  const moduleSwaggerFiles = swaggerFiles.filter(file => file.startsWith('module-') && file.endsWith('.json'));

  if (moduleSwaggerFiles.length === 0) {
    console.log(`No modules found in ${swaggerDir}.`);
    return;
  }

  console.log(`Found ${moduleSwaggerFiles.length} module(s) for app '${appName}'. Processing...`);

  for (const swaggerFileName of moduleSwaggerFiles) {
    const moduleName = swaggerFileName.replace(`module-${appName}-`, '').replace('.json', '');
    const swaggerFilePath = path.join(swaggerDir, swaggerFileName);

    try {
      console.log(`\n--- Generating actions for module: ${moduleName} ---`);
      await generateActionsForSwaggerFile(swaggerFilePath, appName, moduleName, smartDocTypes);
      console.log(`--- Finished generating actions for module: ${moduleName} ---`);
    } catch (error) {
      console.error(`Error processing app '${appName}' module '${moduleName}':`, error.message);
    }
  }

  console.log(`\nAll modules for app '${appName}' processed.`);
}

main();
