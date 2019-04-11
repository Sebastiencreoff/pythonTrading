import json
import logging
import os.path

import coinbase.wallet.client

import trading.connection.connection

REF_CURRENCY = 'EUR'


class CoinBaseConnect(trading.connection.connection.Connect):
    """coinBase API connection."""
    
    def __init__(self, config_dict):
        """Initialisation of all configuration needed.

        :param config_dict: configuration dictionary for connection

        configuration example:

            'configDict' : 'config/coinBase.json'
            'simulation' : No

            and configDict is a jso0n file which contained:
            {'api_key' : xxxx , 'api_secret' : xxx, 'simulation' : true }

        """
        logging.info('')

        assert os.path.isfile(config_dict)
        self.__dict__ = json.load(open(config_dict, mode='r'))
        self.simulation = self.__dict__.get('simulation', True)

        self.client = coinbase.wallet.client.Client(
            self.__dict__.get('api_key', None),
            self.__dict__.get('api_secret', None))

        # Check payment method
        self.payment_method = None

        logging.debug('coinbase payment_method: %s',
                      self.client.get_payment_methods())

        for payment_method in self.client.get_payment_methods().data:
            if payment_method['type'] == 'fiat_account':
                self.payment_method = payment_method

        if not self.payment_method:
            logging.critical('fiat_account not found')
            raise NameError('Only fiat_account is accepted')

        logging.info('coinbase payment_method id: %s', self.payment_method.id)
        super().__init__(config_dict)

    def _get_account_id(self, currency):
        for account in self.client.get_accounts().data:
            if account['currency'] == currency:
                return account

        logging.critical('account not found for currency: %s', currency)
        raise NameError('Invalid currency')

    def get_value(self, currency=None):
        """Get currencies from coinBase in EUR.

            :param currency: currency value to get

            :return : value of the currency

            :raise NameError: if currency not found
            :example :
                >>> get_currency(currency='BTC')
                920
        """
        rates = self.client.get_exchange_rates(currency=currency)

        if isinstance(rates, dict):
            logging.info('%s', rates['rates'][REF_CURRENCY])
            return float(rates['rates'][REF_CURRENCY])
        
        logging.error('error in response')
        return None

    def buy(self, amount, currency, currency_value):
        """Buy currency in EUR, currency is defined at class initialisation.

            :param amount: amount value
            :param currency: currency to buy
            :param currency_value: current currency value.
            :return : currency_value bought and fee amount.
            :example :
            >>> buy_currency(amount=10)
                0.2, 0.01
        """
        try:
            buy = self.client.buy(self._get_account_id(currency).id,
                                  amount=amount,
                                  currency=REF_CURRENCY,
                                  payment_method=self.payment_method.id,
                                  quote=self.simulation)

        except coinbase.wallet.errors.CoinbaseError as e:
            logging.critical('Buy error: {}'.format(e))
        else:
            logging.debug('response: %s', buy)

            logging.warning('success currency: %s '
                            'amount: %s/%s (%s in %s) '
                            'fee_amount: %s',
                            currency,
                            buy.amount.amount,
                            buy.subtotal.amount,
                            currency_value,
                            REF_CURRENCY,
                            buy.fee.amount)
            return float(buy.amount.amount), float(buy.fee.amount)
        return None, None

    def sell(self, amount, currency, currency_value):
        """Sell currency, currency is defined at class initialisation.

            :param amount: amount value in currency
            :param currency: currency to sell
            :param currency_value: current currency value.
            :return : amount sell in Eur, fee amount in Eur

            :example :
                >>> sell(amount=0.1, currency='BTC')
                10.1, 0.1
        """

        try:
            sell = self.client.sell(self._get_account_id(currency).id,
                                    amount=amount,
                                    currency=currency,
                                    payment_method=self.payment_method.id,
                                    quote=self.simulation)

        except coinbase.wallet.errors.CoinbaseError as e:
            logging.critical('Sell error: {}'.format(e))
        else:
            logging.debug('response: %s', sell)

            logging.warning('success currency: %s '
                            'amount: %s/%s (%s in %s),'
                            'fee_amount: %s',
                            currency,
                            sell.amount.amount,
                            sell.subtotal.amount,
                            currency_value,
                            REF_CURRENCY,
                            sell.fee.amount)
            return float(sell.subtotal.amount), float(sell.fee.amount)
        return None, None
