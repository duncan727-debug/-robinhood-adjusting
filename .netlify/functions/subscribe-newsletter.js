const HUBSPOT_API_KEY = process.env.HUBSPOT_API_KEY;

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    const body = JSON.parse(event.body);
    const { email, segment } = body;

    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Invalid email address' })
      };
    }

    const validSegments = ['homeowner', 'service-provider', 'real-estate'];
    const normalizedSegment = segment?.toLowerCase().replace(/\s+/g, '-');
    if (!validSegments.includes(normalizedSegment)) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Invalid segment selection' })
      };
    }

    const segmentListMap = {
      'homeowner': process.env.HUBSPOT_LIST_HOMEOWNERS,
      'service-provider': process.env.HUBSPOT_LIST_SERVICE_PROVIDERS,
      'real-estate': process.env.HUBSPOT_LIST_RE_PROFESSIONALS
    };
    const listId = segmentListMap[normalizedSegment];

    // Create contact (v3 API uses properties as object, not array)
    const createResponse = await fetch('https://api.hubapi.com/crm/v3/objects/contacts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HUBSPOT_API_KEY}`
      },
      body: JSON.stringify({
        properties: {
          email,
          lifecyclestage: 'subscriber'
        }
      })
    });

    let contactId;

    if (!createResponse.ok) {
      if (createResponse.status === 409) {
        // Contact already exists — look them up and update segment
        const result = await updateExistingContact(email, normalizedSegment, listId);
        return result;
      }
      const error = await createResponse.text();
      console.error('HubSpot create error:', error);
      return {
        statusCode: createResponse.status,
        body: JSON.stringify({ error: 'Failed to subscribe. Please try again.' })
      };
    }

    const data = await createResponse.json();
    contactId = data.id;

    if (listId) {
      await addContactToList(contactId, listId);
    }

    return {
      statusCode: 200,
      body: JSON.stringify({ success: true, contact_id: contactId, message: 'Successfully subscribed!' })
    };

  } catch (error) {
    console.error('Newsletter subscription error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error' })
    };
  }
};

async function updateExistingContact(email, segment, listId) {
  try {
    const searchResponse = await fetch('https://api.hubapi.com/crm/v3/objects/contacts/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HUBSPOT_API_KEY}`
      },
      body: JSON.stringify({
        filterGroups: [{
          filters: [{ propertyName: 'email', operator: 'EQ', value: email }]
        }]
      })
    });

    if (!searchResponse.ok) {
      return { statusCode: 500, body: JSON.stringify({ error: 'Failed to locate contact' }) };
    }

    const searchData = await searchResponse.json();
    if (!searchData.results?.length) {
      return { statusCode: 404, body: JSON.stringify({ error: 'Contact not found' }) };
    }

    const contactId = searchData.results[0].id;

    const updateResponse = await fetch(`https://api.hubapi.com/crm/v3/objects/contacts/${contactId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HUBSPOT_API_KEY}`
      },
      body: JSON.stringify({ properties: {} })
    });

    if (!updateResponse.ok) {
      return { statusCode: 500, body: JSON.stringify({ error: 'Failed to update contact segment' }) };
    }

    if (listId) {
      await addContactToList(contactId, listId);
    }

    return {
      statusCode: 200,
      body: JSON.stringify({ success: true, contact_id: contactId, message: 'Contact updated successfully!' })
    };

  } catch (error) {
    console.error('Update contact error:', error);
    return { statusCode: 500, body: JSON.stringify({ error: 'Internal server error' }) };
  }
}

async function addContactToList(contactId, listId) {
  try {
    const response = await fetch(`https://api.hubapi.com/crm/v3/lists/${listId}/memberships/add`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HUBSPOT_API_KEY}`
      },
      body: JSON.stringify([String(contactId)])
    });

    if (!response.ok) {
      console.error('Failed to add contact to list:', response.status, await response.text());
    }
    return response.ok;
  } catch (error) {
    console.error('Add to list error:', error);
    return false;
  }
}
