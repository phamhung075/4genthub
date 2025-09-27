var fs = require('fs');

var preDeployFunction = function (captainAppObj, dockerUpdateObject) {
    return Promise.resolve()
        .then(function(){
            console.log('🚀 CapRover Pre-Deploy Function Starting...');
            
            // Get app name from captain app object
            var appName = captainAppObj.appName || '';
            console.log('📦 App Name:', appName);
            
            var templateFile;
            var appType;
            
            // Determine which template to use based on app name
            if (appName.indexOf('api') !== -1) {
                templateFile = 'captain-definition.backend';
                appType = 'backend';
                console.log('🔧 Detected API app - using BACKEND configuration');
            } else if (appName.indexOf('webapp') !== -1) {
                templateFile = 'captain-definition.frontend';
                appType = 'frontend';
                console.log('🎨 Detected WEBAPP app - using FRONTEND configuration');
            } else {
                // Default to backend if type cannot be determined
                templateFile = 'captain-definition.backend';
                appType = 'backend';
                console.log('⚠️ Unable to detect app type from name - defaulting to BACKEND');
            }
            
            console.log('📄 Template file:', templateFile);
            console.log('🏷️ App type:', appType);
            
            // Copy template file to captain-definition
            try {
                if (fs.existsSync(templateFile)) {
                    console.log('✅ Template file exists, copying to captain-definition...');
                    var templateContent = fs.readFileSync(templateFile, 'utf8');
                    fs.writeFileSync('captain-definition', templateContent);
                    console.log('✅ Successfully copied template to captain-definition');
                    
                    // Log the content for verification
                    console.log('📋 Captain-definition content:');
                    console.log(templateContent);
                } else {
                    console.log('⚠️ Template file not found, creating fallback definition...');
                    // Fallback: create basic definition if template doesn't exist
                    var fallbackDefinition = {
                        "schemaVersion": 2,
                        "dockerfilePath": "./docker-system/docker/Dockerfile." + appType + ".production"
                    };
                    var fallbackContent = JSON.stringify(fallbackDefinition, null, 2);
                    fs.writeFileSync('captain-definition', fallbackContent);
                    console.log('✅ Fallback captain-definition created');
                    console.log('📋 Fallback content:', fallbackContent);
                }
            } catch (error) {
                console.error('❌ Error during file operations:', error.message);
                console.log('🔄 Continuing with existing captain-definition...');
            }
            
            console.log('🏷️ Adding deployment metadata to Docker labels...');
            
            // Add deployment metadata to docker labels
            if (!dockerUpdateObject.TaskTemplate) {
                dockerUpdateObject.TaskTemplate = {};
            }
            if (!dockerUpdateObject.TaskTemplate.ContainerSpec) {
                dockerUpdateObject.TaskTemplate.ContainerSpec = {};
            }
            if (!dockerUpdateObject.TaskTemplate.ContainerSpec.Labels) {
                dockerUpdateObject.TaskTemplate.ContainerSpec.Labels = {};
            }
            
            // Add deployment tracking
            var deploymentType = appName.indexOf('api') !== -1 ? 'backend' : 
                                appName.indexOf('webapp') !== -1 ? 'frontend' : 'backend';
            var deploymentTimestamp = new Date().toISOString();
            
            dockerUpdateObject.TaskTemplate.ContainerSpec.Labels['deployment.type'] = deploymentType;
            dockerUpdateObject.TaskTemplate.ContainerSpec.Labels['deployment.timestamp'] = deploymentTimestamp;
            dockerUpdateObject.TaskTemplate.ContainerSpec.Labels['deployment.app-name'] = appName;
                
            if (captainAppObj.deployedVersion) {
                dockerUpdateObject.TaskTemplate.ContainerSpec.Labels['deployment.version'] = 
                    captainAppObj.deployedVersion + '';
                console.log('📝 Added labels - Type:', deploymentType, 'Version:', captainAppObj.deployedVersion, 'Timestamp:', deploymentTimestamp);
            } else {
                console.log('📝 Added labels - Type:', deploymentType, 'Timestamp:', deploymentTimestamp);
            }
            
            console.log('✅ Pre-deploy function completed successfully!');
            
            // Return the modified docker update object
            return dockerUpdateObject;
        });
};