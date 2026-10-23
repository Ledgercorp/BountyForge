// Owned, model-free observer. No provider, shell, filesystem or verifier access.
// Uses the pinned release's documented Cordis and tools APIs, not Node patches.
export const name = 'bountyforge-runtime-audit';
export const inject = ['tools'];
export function apply(ctx) {
  let requests = 0;
  ctx.on('agent/request', () => {
    requests++;
    throw Error('BountyForge model-free acceptance prohibits inference');
  });
  ctx.on('agent/created', async ({agent}) => {
    const tools = ctx.get('tools');
    const names = tools.schemas(agent).map(x => x.name).sort();
    const forbidden = ['bash','pwsh','exec_command','write_stdin','write','edit','read','read_image',
      'list_mcp_resources','list_mcp_resource_templates','read_mcp_resource','run_code'];
    const refusals = [];
    for (const tool of forbidden) {
      const available = tools.resolveExecution(tool, agent, false) !== undefined;
      // Never invoke a forbidden body if the profile accidentally exposes it.
      if (available) { refusals.push({tool,available:true,invoked:false}); continue; }
      const result = await tools.execute({name:tool, arguments:{}, agent,
        callId:'bountyforge-negative-'+tool, signal:AbortSignal.timeout(1000)});
      refusals.push({tool,available:false,invoked:true,
        unknown_tool:JSON.stringify(result).includes('UNKNOWN_TOOL')});
    }
    const report = {kind:'BOUNTYFORGE_LIVE_SDK_CAPABILITY_AUDIT',tool_names:names,
      refusals,model_requests:requests,mcp_resources_service_present:ctx.get('mcpResources')!==undefined};
    process.stderr.write('BOUNTYFORGE_AUDIT '+JSON.stringify(report)+'\n');
  });
}
