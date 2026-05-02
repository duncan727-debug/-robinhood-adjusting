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

    // Validate email
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Invalid email address' })
      };
    }

    // Validate segment
    const validSegments = ['homeowner', 'provider', 're-professional'];
    const normalizedSegment = segment?.toLowerCase().replace(/\s+/g, '-');
    if (!validSegments.includes(normalizedSegment)) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Invalid segment selection' })
      };
    }

    // Create or update contact in HubSpot
    const response = await fetch('https://api.hubapi.com/crm/v3/objects/contacts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HUBSPOT_API_KEY}`
      },
      body: JSON.stringify({
        properties: [
          {
            name: 'email',
            value: email
          },
          {
            name: 'audience_segment',
            value: normalizedSegment
          },
          {
            name: 'hs_lead_status',
            value: 'subscriber'
          },
          {
            name: 'lifecyclestage',
            value: 'subscriber'
          }
        ]
      })
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('HubSpot API error:', error);

      // Check if it's a duplicate (contact already exists)
      if (response.status === 409) {
        console.log('Contact already exists, updating segment');
        // Try to update existing contact instead
        return await updateExistingContact(email, normalizedSegment);
      }

      return {
        statusCode: response.status,
        body: JSON.stringify({ error: 'Failed to subscribe. Please try again.' })
      };
    }

    const data = await response.json();
    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        contact_id: data.id,
        message: 'Successfully subscribed!'
      })
    };
  } catch (error) {
    console.error('Newsletter subscription error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error' })
    };
  }
};

async function updateExistingContact(email, segment) {
  try {
    const response = await fetch(
      `https://api.hubapi.com/crm/v3/objects/contacts?limit=1&after=0&properties=email`,
      {
        headers: {
          'Authorization': `Bearer ${HUBSPOT_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Could not find contact' })
      };
    }

    // Search for contact by email using the search API
    const searchResponse = await fetch('https://api.hubapi.com/crm/v3/objects/contacts/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HUBSPOT_API_KEY}`
      },
      body: JSON.stringify({
        filterGroups: [
          {
            filters: [
              {
                propertyName: 'email',
                operator: 'EQ',
                value: email
              }
            ]
          }
        ]
      })
    });

    if (!searchResponse.ok) {
      return {
        statusCode: 500,
        body: JSON.stringify({ error: 'Failed to update contact' })
      };
    }

    const searchData = await searchResponse.json();
    if (!searchData.results || searchData.results.length === 0) {
      return {
        statusCode: 404,
        body: JSON.stringify({ error: 'Contact not found' })
      };
    }

    const contactId = searchData.results[0].id;

    // Update the contact with new segment
    const updateResponse = await fetch(
      `https://api.hubapi.com/crm/v3/objects/contacts/${contactId}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${HUBSPOT_API_KEY}`
        },
        body: JSON.stringify({
          properties: [
            {
              name: 'audience_segment',
              value: segment
            }
          ]
        })
      }
    );

    if (!updateResponse.ok) {
      return {
        statusCode: 500,
        body: JSON.stringify({ error: 'Failed to update contact segment' })
      };
    }

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        contact_id: contactId,
        message: 'Contact updated successfully!'
      })
    };
  } catch (error) {
    console.error('Update contact error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error' })
    };
  }
}
