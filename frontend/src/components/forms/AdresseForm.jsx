import React from 'react';
import { Controller } from 'react-hook-form';

const AdresseForm = ({ name, control, errors }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="md:col-span-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Rue *
        </label>
        <Controller
          name={`${name}.rue`}
          control={control}
          render={({ field }) => (
            <input
              {...field}
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="Numéro et nom de rue"
            />
          )}
        />
        {errors?.rue && (
          <p className="mt-1 text-sm text-red-600">{errors.rue.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Ville *
        </label>
        <Controller
          name={`${name}.ville`}
          control={control}
          render={({ field }) => (
            <input
              {...field}
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="Ville"
            />
          )}
        />
        {errors?.ville && (
          <p className="mt-1 text-sm text-red-600">{errors.ville.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Code postal *
        </label>
        <Controller
          name={`${name}.code_postal`}
          control={control}
          render={({ field }) => (
            <input
              {...field}
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="Code postal"
            />
          )}
        />
        {errors?.code_postal && (
          <p className="mt-1 text-sm text-red-600">{errors.code_postal.message}</p>
        )}
      </div>

      <div className="md:col-span-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Pays *
        </label>
        <Controller
          name={`${name}.pays`}
          control={control}
          render={({ field }) => (
            <select
              {...field}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="Maroc">Maroc</option>
              <option value="France">France</option>
              <option value="Espagne">Espagne</option>
              <option value="Algérie">Algérie</option>
              <option value="Tunisie">Tunisie</option>
            </select>
          )}
        />
        {errors?.pays && (
          <p className="mt-1 text-sm text-red-600">{errors.pays.message}</p>
        )}
      </div>
    </div>
  );
};

export default AdresseForm;
