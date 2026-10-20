# POS FBR Integration Module

## Overview

This module integrates Odoo POS with FBR (Federal Board of Revenue) POS system to automatically send order data and retrieve FBR invoice numbers for printing on receipts.

## Features

- **Automatic FBR Integration**: Automatically sends POS order data to FBR POS when payment is completed
- **Invoice Number Retrieval**: Retrieves and stores FBR invoice numbers for each order
- **Enhanced Receipts**: Prints FBR invoice numbers and logos on POS receipts
- **Error Handling**: Comprehensive error handling with retry mechanisms
- **Status Tracking**: Track FBR posting status (draft, posted, failed, pending)
- **QR Code Support**: Generates QR codes for invoice verification
- **Configuration**: Easy setup through POS configuration settings

## Installation

1. Copy the `tt_pos_fbr_integration` folder to your Odoo addons directory
2. Restart Odoo server
3. Update the module list
4. Install the "POS FBR Integration" module

## Configuration

### 1. Configure FBR POS Settings

1. Go to **Point of Sale → Configuration → Point of Sale**
2. Select or create a POS configuration
3. In the "FBR POS Integration" section:
   - Enable "FBR POS Integration"
   - Enter the "FBR POS URL" (API endpoint)
   - Enter the "FBR POS Token" (authentication token)
   - Set the "FBR POS Timeout" (default: 10 seconds)

### 2. Configure FBR Logo (Optional)

1. Go to **Settings → Companies → Your Company**
2. Upload the FBR logo in the "FBR Logo" field

## Usage

### Normal Workflow

1. Create orders in POS as usual
2. When payment is completed, the order data is automatically sent to FBR POS
3. If successful, the FBR invoice number is retrieved and stored
4. The receipt will show:
   - FBR logo
   - FBR invoice number
   - QR code for verification
   - "Verified by FBR" status

### Error Handling

If FBR posting fails:
- The order status will be marked as "Failed"
- Error message will be displayed
- Receipt will show the error status
- Use the "Retry FBR Post" button to retry sending

### Manual Retry

1. Go to the POS order in backend
2. Click "Retry FBR Post" button
3. The system will attempt to resend the order to FBR POS

## Technical Details

### Data Flow

1. **Payment Complete** → `action_pos_order_paid()` triggered
2. **FBR Integration Check** → Verifies if FBR POS integration is enabled
3. **Payload Preparation** → Order data is formatted for FBR POS API
4. **API Request** → Data sent to FBR POS endpoint
5. **Response Processing** → Invoice number extracted and stored
6. **Receipt Enhancement** → FBR information added to receipt

### API Payload Structure

```json
{
  "order_ref": "POS/0001/2024",
  "order_date": "2024-03-11 14:30:00",
  "customer": {
    "name": "Customer Name",
    "phone": "+923001234567",
    "email": "customer@example.com",
    "vat": "1234567890"
  },
  "items": [
    {
      "product_name": "Product Name",
      "quantity": 2,
      "unit_price": 100.00,
      "discount": 0,
      "total_price": 200.00,
      "tax_amount": 30.00
    }
  ],
  "payments": [
    {
      "payment_method": "Cash",
      "amount": 230.00
    }
  ],
  "amounts": {
    "subtotal": 200.00,
    "tax": 30.00,
    "total": 230.00
  }
}
```

### Expected API Response

```json
{
  "success": true,
  "invoice_number": "FBR-2024-0001"
}
```

## Troubleshooting

### Common Issues

1. **FBR POS URL not configured**
   - Solution: Configure the FBR POS URL in POS configuration

2. **Authentication failed**
   - Solution: Verify the FBR POS token is correct

3. **Network timeout**
   - Solution: Increase the FBR POS timeout setting

4. **Invalid payload format**
   - Solution: Check FBR POS API documentation for required format

### Debug Information

All FBR-related data is stored in the POS order:
- `fbr_payload`: Data sent to FBR POS
- `fbr_response`: Response received from FBR POS
- `fbr_error_message`: Error details (if any)

## Cron Jobs

The module includes a cron job to automatically retry failed FBR orders:
- **Cron Job**: `cron_retry_failed_fbr_orders`
- **Frequency**: Every hour (configurable)
- **Purpose**: Retry orders that failed to post to FBR POS

## Dependencies

- `point_of_sale`: Odoo POS module
- `product`: Product management
- `stock`: Stock management
- `base`: Base Odoo functionality

## Compatibility

- Odoo Version: 17.0
- Python Version: 3.8+
- Tested with: Odoo Enterprise and Community

## Support

For support and issues:
- Email: support@tezztareen.com
- Website: https://tezztareen.com/

## License

This module is licensed under LGPL-3.

## Changelog

### Version 1.0
- Initial release
- Basic FBR POS integration
- Receipt enhancement with FBR branding
- Error handling and retry mechanisms
