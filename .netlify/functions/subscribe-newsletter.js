const BEEHIIV_API_KEY = process.env.BEEHIIV_API_KEY || '3Zfh39Nao3CjbTCsuzWgx1wzzUlcgizPrNb3v3e3RQCl8GeFUNJwgdug0FsYm9XI';
const PUBLICATION_ID = 'eac67b70-2653-48ab-b4a0-c8b01533c691';

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    const { email } = JSON.parse(event.body);

    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'Invalid email address' })
      };
    }

    const response = await fetch('https://api.beehiiv.com/v1/subscriptions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${BEEHIIV_API_KEY}`
      },
      body: JSON.stringify({
        email: email,
        publication_id: PUBLICATION_ID
      })
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('Beehiiv API error:', error);
      return {
        statusCode: response.status,
        body: JSON.stringify({ error: 'Failed to subscribe' })
      };
    }

    const data = await response.json();
    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        subscription_id: data.data?.id
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
