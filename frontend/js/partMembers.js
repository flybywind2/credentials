export async function loadReadablePartMembers(fetcher, orgId = null) {
  const suffix = orgId ? `?org_id=${encodeURIComponent(orgId)}` : "";
  try {
    const members = await fetcher(`/api/part-members${suffix}`);
    return Array.isArray(members) ? members : [];
  } catch (error) {
    if (error?.status === 403) {
      return [];
    }
    throw error;
  }
}
